import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import create_app


def _image_bytes(text: str = "Fox Sportz") -> bytes:
    image = np.full((560, 900, 3), 232, dtype=np.uint8)
    cv2.rectangle(image, (55, 55), (845, 505), (255, 255, 255), -1)
    cv2.rectangle(image, (55, 425), (845, 505), (75, 20, 45), -1)
    cv2.putText(image, text, (120, 260), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (20, 20, 20), 3)
    success, encoded = cv2.imencode(".jpg", image)
    assert success
    return encoded.tobytes()


def _create_event_and_session(client: TestClient) -> tuple[dict, dict]:
    event_response = client.post(
        "/api/v1/events",
        json={"title": "Fall Welcome Tabling", "event_type": "TABLING"},
    )
    assert event_response.status_code == 201
    event = event_response.json()
    session_response = client.post(f"/api/v1/events/{event['id']}/sessions", json={})
    assert session_response.status_code == 201
    return event, session_response.json()


def test_health_and_ready(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").status_code == 200


def test_capture_edit_approve_and_resume(client: TestClient, app) -> None:
    event, capture_session = _create_event_and_session(client)
    captured = client.post(
        f"/api/v1/sessions/{capture_session['id']}/cards",
        files={"image": ("capture.jpg", _image_bytes(), "image/jpeg")},
        data={"mock_text": "Fox Sportz"},
    )
    assert captured.status_code == 201
    card = captured.json()
    assert card["status"] == "NEEDS_REVIEW"
    assert card["raw_ocr"] == "Fox Sportz"

    approved_response = client.post(
        f"/api/v1/cards/{card['id']}/approve",
        json={"final_type": "EMPLOYER", "final_text": "Fox Sports"},
    )
    assert approved_response.status_code == 200
    approved = approved_response.json()
    assert approved["final_text"] == "Fox Sports"
    assert approved["raw_ocr"] == "Fox Sportz"
    assert approved["was_edited"] is True
    assert approved["has_image"] is False

    # Simulate a server restart by creating a fresh app/engine against the same DB file.
    restarted_app = create_app(app.state.settings)
    with TestClient(restarted_app) as resumed_client:
        sessions = resumed_client.get("/api/v1/sessions").json()
        assert sessions[0]["id"] == capture_session["id"]
        assert sessions[0]["approved_cards"] == 1
        persisted = resumed_client.get(f"/api/v1/cards/{card['id']}").json()
        assert persisted["final_text"] == "Fox Sports"
        assert persisted["raw_ocr"] == "Fox Sportz"
        event_detail = resumed_client.get(f"/api/v1/events/{event['id']}").json()
        assert event_detail["approved_count"] == 1
    restarted_app.state.engine.dispose()


def test_complete_reopen_and_archive_preserve_session(client: TestClient) -> None:
    _, capture_session = _create_event_and_session(client)
    session_id = capture_session["id"]

    completed = client.post(f"/api/v1/sessions/{session_id}/complete").json()
    assert completed["status"] == "COMPLETED"

    blocked = client.post(
        f"/api/v1/sessions/{session_id}/cards",
        files={"image": ("capture.jpg", _image_bytes(), "image/jpeg")},
    )
    assert blocked.status_code == 409

    reopened = client.post(f"/api/v1/sessions/{session_id}/reopen").json()
    assert reopened["status"] == "IN_PROGRESS"
    assert reopened["completed_at"] is None

    archived = client.post(f"/api/v1/sessions/{session_id}/archive").json()
    assert archived["status"] == "ARCHIVED"
    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 200


def test_rejects_unreadable_image(client: TestClient) -> None:
    _, capture_session = _create_event_and_session(client)
    response = client.post(
        f"/api/v1/sessions/{capture_session['id']}/cards",
        files={"image": ("capture.jpg", b"not-an-image", "image/jpeg")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_IMAGE"


def test_edit_approved_card_preserves_raw_ocr_and_appends_revision(
    client: TestClient,
) -> None:
    _, capture_session = _create_event_and_session(client)
    captured = client.post(
        f"/api/v1/sessions/{capture_session['id']}/cards",
        files={"image": ("capture.jpg", _image_bytes(), "image/jpeg")},
        data={"mock_text": "Fox Sportz"},
    ).json()
    approved = client.post(
        f"/api/v1/cards/{captured['id']}/approve",
        json={"final_type": "EMPLOYER", "final_text": "Fox Sports"},
    ).json()
    client.post(f"/api/v1/sessions/{capture_session['id']}/complete").raise_for_status()

    edited_response = client.patch(
        f"/api/v1/cards/{approved['id']}",
        json={
            "final_type": "EMPLOYER",
            "final_text": "FOX Sports",
            "reason": "Corrected capitalization from the physical card.",
        },
    )
    assert edited_response.status_code == 200
    edited = edited_response.json()
    assert edited["final_text"] == "FOX Sports"
    assert edited["raw_ocr"] == "Fox Sportz"

    revisions = client.get(f"/api/v1/cards/{approved['id']}/revisions").json()
    assert len(revisions) == 1
    assert revisions[0]["revision_number"] == 1
    assert revisions[0]["previous_final_text"] == "Fox Sports"
    assert revisions[0]["new_final_text"] == "FOX Sports"
    assert revisions[0]["reason"] == "Corrected capitalization from the physical card."

    completed_session = client.get(f"/api/v1/sessions/{capture_session['id']}").json()
    assert completed_session["status"] == "COMPLETED"


def test_remove_and_restore_cards_preserves_content_revisions_and_counts(
    client: TestClient,
) -> None:
    event, capture_session = _create_event_and_session(client)
    session_id = capture_session["id"]
    captured = client.post(
        f"/api/v1/sessions/{session_id}/cards",
        files={"image": ("capture.jpg", _image_bytes(), "image/jpeg")},
        data={"mock_text": "Fox Sportz"},
    ).json()
    unsettled_removal = client.delete(f"/api/v1/cards/{captured['id']}")
    assert unsettled_removal.status_code == 409
    assert unsettled_removal.json()["error"]["code"] == "CARD_NOT_SETTLED"
    approved = client.post(
        f"/api/v1/cards/{captured['id']}/approve",
        json={"final_type": "EMPLOYER", "final_text": "Fox Sports"},
    ).json()
    client.patch(
        f"/api/v1/cards/{approved['id']}",
        json={
            "final_type": "EMPLOYER",
            "final_text": "FOX Sports",
            "reason": "Verified capitalization.",
        },
    ).raise_for_status()

    removed_response = client.delete(f"/api/v1/cards/{approved['id']}")
    assert removed_response.status_code == 200
    removed = removed_response.json()
    assert removed["status"] == "REMOVED"
    assert removed["raw_ocr"] == "Fox Sportz"
    assert removed["final_text"] == "FOX Sports"
    assert removed["removed_at"] is not None
    assert removed["removed_reason"] == "Removed by operator."
    assert client.get(f"/api/v1/sessions/{session_id}/cards").json() == []

    cards_with_removed = client.get(
        f"/api/v1/sessions/{session_id}/cards?include_removed=true"
    ).json()
    assert [item["id"] for item in cards_with_removed] == [approved["id"]]
    revisions = client.get(f"/api/v1/cards/{approved['id']}/revisions").json()
    assert len(revisions) == 1
    assert revisions[0]["previous_final_text"] == "Fox Sports"
    session_without_removed = client.get(f"/api/v1/sessions/{session_id}").json()
    assert session_without_removed["total_cards"] == 0
    assert session_without_removed["approved_cards"] == 0
    event_without_removed = client.get(f"/api/v1/events/{event['id']}").json()
    assert event_without_removed["card_count"] == 0

    restored_response = client.post(f"/api/v1/cards/{approved['id']}/restore")
    assert restored_response.status_code == 200
    restored = restored_response.json()
    assert restored["status"] == "APPROVED"
    assert restored["raw_ocr"] == "Fox Sportz"
    assert restored["final_text"] == "FOX Sports"
    assert restored["removed_at"] is None
    assert len(client.get(f"/api/v1/sessions/{session_id}/cards").json()) == 1
    restored_session = client.get(f"/api/v1/sessions/{session_id}").json()
    assert restored_session["total_cards"] == 1
    assert restored_session["approved_cards"] == 1

    skipped_capture = client.post(
        f"/api/v1/sessions/{session_id}/cards",
        files={"image": ("capture.jpg", _image_bytes("Skip me"), "image/jpeg")},
        data={"mock_text": "Skip me"},
    ).json()
    skipped = client.post(f"/api/v1/cards/{skipped_capture['id']}/skip").json()
    assert skipped["has_image"] is True
    removed_skipped = client.delete(f"/api/v1/cards/{skipped['id']}").json()
    assert removed_skipped["status"] == "REMOVED"
    assert removed_skipped["has_image"] is False
    assert client.get(f"/api/v1/cards/{skipped['id']}/image").status_code == 404
    restored_skipped = client.post(f"/api/v1/cards/{skipped['id']}/restore").json()
    assert restored_skipped["status"] == "SKIPPED"


def test_update_and_archive_event_preserves_sessions(client: TestClient) -> None:
    event, capture_session = _create_event_and_session(client)
    updated_response = client.patch(
        f"/api/v1/events/{event['id']}",
        json={
            "title": "Updated Career Fair",
            "event_type": "OTHER",
            "event_date": "2026-09-15",
            "location": "Student Pavilion",
            "topic": "Employer networking",
        },
    )
    assert updated_response.status_code == 200
    updated = updated_response.json()
    assert updated["title"] == "Updated Career Fair"
    assert updated["location"] == "Student Pavilion"

    archived_response = client.delete(f"/api/v1/events/{event['id']}")
    assert archived_response.status_code == 200
    assert archived_response.json()["is_archived"] is True
    assert all(item["id"] != event["id"] for item in client.get("/api/v1/events").json())
    archived_events = client.get("/api/v1/events?include_archived=true").json()
    assert any(item["id"] == event["id"] for item in archived_events)
    assert all(
        item["id"] != capture_session["id"] for item in client.get("/api/v1/sessions").json()
    )
    assert client.get(f"/api/v1/sessions/{capture_session['id']}").status_code == 200
