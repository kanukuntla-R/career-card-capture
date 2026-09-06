# Camera and Vision Pipeline

## Goal

Make physical card entry behave like a lightweight scanner using a normal 1080p webcam.

## Browser camera

Use `navigator.mediaDevices.getUserMedia`.

Preferred constraints:

- video enabled
- request 1920x1080 ideal when supported
- do not fail if camera supplies a lower resolution
- audio disabled

The browser must show:

- live preview
- card placement guide
- camera selector where needed
- capture status
- permission/error guidance

Remote camera access requires a secure browser context. `localhost` works for local development; private remote deployment should use HTTPS over the Tailnet rather than public exposure.

## Capture modes

### Mode 1: manual capture — implement first

Operator positions card and presses:

- capture button, or
- `Space` when not typing.

This creates the first reliable vertical slice.

### Mode 2: assisted auto-capture — add after manual flow is stable

State machine:

```text
WAITING_FOR_CARD
    -> CARD_DETECTED
    -> WAITING_FOR_STABILITY
    -> CAPTURE
    -> PROCESSING
    -> REVIEW
    -> WAITING_FOR_REMOVAL
    -> WAITING_FOR_CARD
```

Do not repeatedly capture the same physical card. Require card removal or significant scene change before arming again.

## Server-side image pipeline

Recommended stages:

1. decode image
2. sanity-check resolution/format
3. detect card contour
4. estimate corners
5. perspective transform
6. detect orientation
7. normalize to canonical orientation
8. crop branded strip / isolate response region
9. optional grayscale/contrast/sharpness normalization
10. produce OCR input + preview artifact
11. compute quality metrics

## Why the card design helps

The known cards include a dark branded strip and a large light response area. This can help with:

- card localization,
- orientation,
- response-region cropping.

Do not assume exact pixel coordinates; detect from normalized card geometry and keep crop ratios configurable.

## Card detection strategy

Start simple:

- edge detection
- contour approximation
- quadrilateral filtering
- aspect-ratio/area checks

Avoid ML card detectors until classical CV proves inadequate.

Fallback:

- if contour confidence is low, use the whole captured image or allow manual crop rather than failing the record.

## Orientation

Use multiple cues:

- location of dark branded strip
- card aspect ratio
- OCR orientation evidence if provider supports it

The normalized OCR image should contain primarily the white handwriting area, reducing printed brand text reaching OCR.

## Preprocessing variants

Do not assume one preprocessing path wins for handwriting.

Benchmark variants:

- original normalized crop
- grayscale
- CLAHE/contrast normalization
- light denoise
- adaptive threshold only if evidence supports it

Aggressive thresholding can destroy thin pencil strokes. Keep the original normalized crop available to the OCR provider.

## Stability detection for auto-capture

Possible lightweight method:

- detect card contour each frame at reduced resolution,
- compare corner movement over N frames,
- optionally compare image difference/blur,
- require stable geometry for ~0.5–1.0 seconds,
- capture one high-resolution frame.

All thresholds are config constants and must be tunable.

## Quality signals

Useful signals:

- detected card area ratio
- perspective confidence
- blur score
- exposure/brightness
- stability score

These can influence whether auto-capture proceeds but should not prevent manual capture.

## Image format

Use JPEG or WebP for transfer, with enough quality to preserve pencil/pen strokes.

Do not repeatedly re-encode through multiple lossy stages.

## Privacy/retention

See `SECURITY_PRIVACY.md`. The capture image is operational data, not a permanent requirement. Default toward deleting after approval unless policy explicitly supports retention.
