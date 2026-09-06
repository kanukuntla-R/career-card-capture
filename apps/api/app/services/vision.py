from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


class VisionError(ValueError):
    """Captured bytes are not a usable image."""


@dataclass(frozen=True)
class VisionResult:
    normalized_image: bytes
    ocr_image: bytes
    metrics: dict[str, Any]


def _order_points(points: np.ndarray) -> np.ndarray:
    ordered = np.zeros((4, 2), dtype=np.float32)
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).reshape(-1)
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(differences)]
    ordered[3] = points[np.argmax(differences)]
    return ordered


def _warp(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    top_left, top_right, bottom_right, bottom_left = _order_points(points)
    width = int(
        max(np.linalg.norm(bottom_right - bottom_left), np.linalg.norm(top_right - top_left))
    )
    height = int(
        max(np.linalg.norm(top_right - bottom_right), np.linalg.norm(top_left - bottom_left))
    )
    width = max(width, 320)
    height = max(height, 180)
    destination = np.array(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(_order_points(points), destination)
    return cv2.warpPerspective(image, matrix, (width, height))


def _orient_brand_strip(image: np.ndarray) -> tuple[np.ndarray, str, float]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    band_y = max(4, int(height * 0.16))
    band_x = max(4, int(width * 0.16))
    means = {
        "top": float(gray[:band_y, :].mean()),
        "bottom": float(gray[-band_y:, :].mean()),
        "left": float(gray[:, :band_x].mean()),
        "right": float(gray[:, -band_x:].mean()),
    }
    darkest = min(means, key=means.get)
    sorted_means = sorted(means.values())
    contrast = sorted_means[1] - sorted_means[0]
    if contrast < 12:
        return image, "unknown", contrast
    rotations = {"bottom": 0, "top": 2, "left": 1, "right": 3}
    return np.ascontiguousarray(np.rot90(image, rotations[darkest])), darkest, contrast


def _encode_jpeg(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 94])
    if not success:
        raise VisionError("The captured image could not be encoded.")
    return encoded.tobytes()


def process_card_image(content: bytes) -> VisionResult:
    image = cv2.imdecode(np.frombuffer(content, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise VisionError("The captured file is not a readable image.")

    original_height, original_width = image.shape[:2]
    if min(original_height, original_width) < 120:
        raise VisionError("The captured image is too small for OCR.")

    scale = min(1.0, 1400 / max(original_height, original_width))
    detection = (
        cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        if scale < 1.0
        else image.copy()
    )
    gray = cv2.cvtColor(detection, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 45, 140)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    frame_area = detection.shape[0] * detection.shape[1]
    quadrilateral: np.ndarray | None = None
    area_ratio = 0.0
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:15]:
        perimeter = cv2.arcLength(contour, True)
        candidate = cv2.approxPolyDP(contour, 0.025 * perimeter, True)
        candidate_ratio = cv2.contourArea(candidate) / frame_area
        if len(candidate) == 4 and candidate_ratio >= 0.16 and cv2.isContourConvex(candidate):
            quadrilateral = candidate.reshape(4, 2).astype(np.float32) / scale
            area_ratio = float(candidate_ratio)
            break

    detected = quadrilateral is not None
    normalized = _warp(image, quadrilateral) if detected else image.copy()
    if normalized.shape[0] > normalized.shape[1]:
        normalized = np.ascontiguousarray(np.rot90(normalized, 1))

    normalized, strip_edge, strip_contrast = _orient_brand_strip(normalized)
    height, width = normalized.shape[:2]
    inset_x = max(1, int(width * 0.025))
    inset_y = max(1, int(height * 0.035))
    crop_bottom = int(height * 0.82) if strip_edge != "unknown" else height - inset_y
    ocr_crop = normalized[inset_y:crop_bottom, inset_x : width - inset_x]
    if ocr_crop.size == 0:
        ocr_crop = normalized

    metrics = {
        "card_detected": detected,
        "card_area_ratio": round(area_ratio, 4),
        "original_width": original_width,
        "original_height": original_height,
        "normalized_width": int(normalized.shape[1]),
        "normalized_height": int(normalized.shape[0]),
        "brand_strip_edge": strip_edge,
        "brand_strip_contrast": round(strip_contrast, 2),
        "blur_score": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2),
        "brightness": round(float(gray.mean()), 2),
    }
    return VisionResult(
        normalized_image=_encode_jpeg(normalized),
        ocr_image=_encode_jpeg(ocr_crop),
        metrics=metrics,
    )
