import csv
import io

import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.services.sheets.types import SHEET_HEADERS, SheetSyncError


class FakeSheetGateway:
    def __init__(self) -> None:
        self.rows: list[list[str]] = [list(SHEET_HEADERS)]
        self.update_count = 0
        self.fail_after_next_append = False

    def ensure_schema(self) -> None:
        if self.rows[0] != list(SHEET_HEADERS):
            raise SheetSyncError("Unexpected test header.")

    def find_record_row(self, record_id: str, cached_row: int | None = None) -> int | None:
        if cached_row and cached_row <= len(self.rows):
            if self.rows[cached_row - 1][0] == record_id:
                return cached_row
        for row_number, row in enumerate(self.rows[1:], start=2):
            if row[0] == record_id:
                return row_number
        return None

    def append_row(self, values: list[str]) -> int:
        self.rows.append(list(values))
        row_number = len(self.rows)
        if self.fail_after_next_append:
            self.fail_after_next_append = False
            raise SheetSyncError("The response was lost after append.")
        return row_number

    def update_row(self, row_number: int, values: list[str]) -> None:
        self.rows[row_number - 1] = list(values)
        self.update_count += 1


def _image_bytes() -> bytes:
    image = np.full((560, 900, 3), 232, dtype=np.uint8)
    cv2.rectangle(image, (55, 55), (845, 505), (255, 255, 255), -1)
    cv2.putText(image, "Fox Sportz", (120, 260), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (20, 20, 20), 3)
    success, encoded = cv2.imencode(".jpg", image)
    assert success
    return encoded.tobytes()


def _approved_card(client: TestClient) -> tuple[dict, dict, dict]:
    event = client.post(
        "/api/v1/events",
        json={"title": "Fall Welcome", "event_type": "TABLING"},
    ).json()
    capture_session = client.post(f"/api/v1/events/{event['id']}/sessions", json={}).json()
    captured = client.post(
        f"/api/v1/sessions/{capture_session['id']}/cards",
        files={"image": ("capture.jpg", _image_bytes(), "image/jpeg")},
        data={"mock_text": "Fox Sportz"},
    ).json()
    approved = client.post(
        f"/api/v1/cards/{captured['id']}/approve",
        json={"final_type": "EMPLOYER", "final_text": "Fox Sports"},
    ).json()
    return event, capture_session, approved


def _enable_fake_sheets(app) -> FakeSheetGateway:
    app.state.settings.google_sheets_enabled = True
    app.state.settings.google_sheet_id = "test-sheet-id"
    app.state.settings.google_sheet_tab_name = "Responses"
    gateway = FakeSheetGateway()
    app.state.sheet_gateway = gateway
    return gateway


def test_sync_appends_once_then_updates_same_row(client: TestClient, app) -> None:
    gateway = _enable_fake_sheets(app)
    event, _, approved = _approved_card(client)
    assert approved["sync_status"] == "PENDING"
    assert client.get("/api/v1/sync/status").json()["pending"] == 1

    first_sync = client.post("/api/v1/sync/retry")
    assert first_sync.status_code == 200
    assert first_sync.json()["succeeded"] == 1
    assert len(gateway.rows) == 2
    assert gateway.rows[1][0] == approved["id"]
    assert gateway.rows[1][6] == "Fox Sports"

    second_sync = client.post("/api/v1/sync/retry")
    assert second_sync.status_code == 200
    assert len(gateway.rows) == 2
    assert gateway.update_count == 0

    edited = client.patch(
        f"/api/v1/cards/{approved['id']}",
        json={"final_type": "EMPLOYER", "final_text": "FOX Sports"},
    ).json()
    assert edited["sync_status"] == "PENDING"
    client.post("/api/v1/sync/retry").raise_for_status()
    assert len(gateway.rows) == 2
    assert gateway.rows[1][6] == "FOX Sports"
    assert gateway.update_count == 1

    client.patch(
        f"/api/v1/events/{event['id']}",
        json={"title": "Updated Fall Welcome"},
    ).raise_for_status()
    assert client.get(f"/api/v1/cards/{approved['id']}").json()["sync_status"] == "PENDING"
    client.post("/api/v1/sync/retry").raise_for_status()
    assert gateway.rows[1][2] == "Updated Fall Welcome"
    assert len(gateway.rows) == 2


def test_retry_after_lost_append_response_does_not_duplicate(client: TestClient, app) -> None:
    gateway = _enable_fake_sheets(app)
    _, _, approved = _approved_card(client)
    gateway.fail_after_next_append = True

    failed = client.post("/api/v1/sync/retry")
    assert failed.status_code == 200
    assert failed.json()["failed"] == 1
    assert failed.json()["errors"] == 1
    assert len(gateway.rows) == 2

    retried = client.post(f"/api/v1/sync/cards/{approved['id']}/retry")
    assert retried.status_code == 200
    assert retried.json()["succeeded"] == 1
    assert len(gateway.rows) == 2
    assert gateway.rows[1][0] == approved["id"]


def test_removed_synced_card_is_tombstoned_and_restore_updates_row(
    client: TestClient, app
) -> None:
    gateway = _enable_fake_sheets(app)
    _, _, approved = _approved_card(client)
    client.post("/api/v1/sync/retry").raise_for_status()

    removed = client.delete(f"/api/v1/cards/{approved['id']}").json()
    assert removed["sync_status"] == "PENDING"
    client.post(f"/api/v1/sync/cards/{approved['id']}/retry").raise_for_status()
    assert gateway.rows[1][0] == approved["id"]
    assert gateway.rows[1][1:7] == ["", "", "", "", "", ""]

    restored = client.post(f"/api/v1/cards/{approved['id']}/restore").json()
    assert restored["sync_status"] == "PENDING"
    client.post(f"/api/v1/sync/cards/{approved['id']}/retry").raise_for_status()
    assert gateway.rows[1][6] == "Fox Sports"
    assert len(gateway.rows) == 2


def test_csv_export_works_without_google_credentials(client: TestClient) -> None:
    _, _, approved = _approved_card(client)
    response = client.get("/api/v1/export/cards.csv")
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == list(SHEET_HEADERS)
    assert rows[1][0] == approved["id"]
    assert rows[1][6] == "Fox Sports"

    status = client.get("/api/v1/sync/status").json()
    assert status["enabled"] is False
    assert status["configured"] is False
    assert status["eligible_cards"] == 1
