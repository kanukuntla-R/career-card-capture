import cv2
import numpy as np

from app.services.vision import process_card_image


def test_normalizes_card_and_excludes_dark_brand_strip() -> None:
    image = np.full((800, 1280, 3), 190, dtype=np.uint8)
    card = np.array([[150, 125], [1130, 90], [1170, 690], [110, 725]], np.int32)
    cv2.fillConvexPoly(image, card, (252, 252, 252))
    cv2.fillConvexPoly(
        image,
        np.array([[115, 620], [1160, 585], [1170, 690], [110, 725]], np.int32),
        (65, 18, 42),
    )
    cv2.putText(
        image,
        "What makes a great leader?",
        (250, 360),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.5,
        (20, 20, 20),
        3,
    )
    success, encoded = cv2.imencode(".jpg", image)
    assert success

    result = process_card_image(encoded.tobytes())
    normalized = cv2.imdecode(np.frombuffer(result.normalized_image, np.uint8), cv2.IMREAD_COLOR)
    ocr_crop = cv2.imdecode(np.frombuffer(result.ocr_image, np.uint8), cv2.IMREAD_COLOR)

    assert result.metrics["card_detected"] is True
    assert normalized.shape[1] > normalized.shape[0]
    assert ocr_crop.shape[0] < normalized.shape[0]
    assert result.metrics["brand_strip_edge"] == "bottom"
