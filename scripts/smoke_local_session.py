"""Run one complete local HunyuanOCR capture session through the public API."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

import cv2
import httpx
import numpy as np


def sample_card(text: str) -> bytes:
    canvas = np.full((820, 1320, 3), 178, dtype=np.uint8)
    card = np.array([[145, 105], [1170, 72], [1210, 700], [105, 735]], np.int32)
    cv2.fillConvexPoly(canvas, card, (252, 252, 252))
    cv2.polylines(canvas, [card], True, (92, 92, 92), 5)
    cv2.fillConvexPoly(
        canvas,
        np.array([[112, 625], [1198, 592], [1210, 700], [105, 735]], np.int32),
        (61, 17, 42),
    )
    cv2.putText(
        canvas,
        text,
        (205, 365),
        cv2.FONT_HERSHEY_SCRIPT_SIMPLEX,
        2.15,
        (27, 27, 27),
        4,
        cv2.LINE_AA,
    )
    ok, encoded = cv2.imencode(".jpg", canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ok:
        raise RuntimeError("Could not generate the smoke-test card")
    return encoded.tobytes()


def checked(response: httpx.Response) -> dict:
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    with httpx.Client(base_url=args.api, timeout=180) as client:
        ready = checked(client.get("/ready"))
        if not ready["ocr"]["ready"] or ready["ocr"]["provider"] != "hunyuan":
            raise RuntimeError(f"HunyuanOCR is not ready: {ready['ocr']}")

        stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        event = checked(
            client.post(
                "/api/v1/events",
                json={
                    "title": f"Local OCR validation — {stamp}",
                    "event_type": "TABLING",
                },
            )
        )
        session = checked(
            client.post(
                f"/api/v1/events/{event['id']}/sessions",
                json={"name": "Complete HunyuanOCR smoke session"},
            )
        )

        approved_cards = []
        for text, card_type in (
            ("Fox Sports", "EMPLOYER"),
            ("What makes a great leader?", "QUESTION"),
        ):
            captured = checked(
                client.post(
                    f"/api/v1/sessions/{session['id']}/cards",
                    files={"image": ("card.jpg", sample_card(text), "image/jpeg")},
                )
            )
            if captured["status"] != "NEEDS_REVIEW":
                raise RuntimeError(f"OCR failed for {text!r}: {captured}")
            if captured["ocr_provider"] != "hunyuan" or not captured["raw_ocr"]:
                raise RuntimeError(f"Unexpected OCR result: {captured}")
            approved = checked(
                client.post(
                    f"/api/v1/cards/{captured['id']}/approve",
                    json={"final_type": card_type, "final_text": text},
                )
            )
            if approved["raw_ocr"] != captured["raw_ocr"]:
                raise RuntimeError("Approval overwrote the preserved raw OCR")
            approved_cards.append(
                {
                    "sequence": approved["sequence_number"],
                    "raw_ocr": approved["raw_ocr"],
                    "final_text": approved["final_text"],
                    "type": approved["final_type"],
                }
            )

        completed = checked(client.post(f"/api/v1/sessions/{session['id']}/complete"))
        persisted = checked(client.get(f"/api/v1/sessions/{session['id']}/cards"))
        if completed["status"] != "COMPLETED" or completed["approved_cards"] != 2:
            raise RuntimeError(f"Session did not complete correctly: {completed}")
        if len(persisted) != 2 or any(
            card["status"] != "APPROVED" for card in persisted
        ):
            raise RuntimeError("Approved cards were not persisted")

        print(
            {
                "event_id": event["id"],
                "session_id": session["id"],
                "status": completed["status"],
                "approved_cards": completed["approved_cards"],
                "cards": approved_cards,
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
