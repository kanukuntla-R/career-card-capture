# OCR Design

## Objective

Transcribe short handwritten card responses and suggest whether the text is an employer name or a question.

The OCR layer must be replaceable because handwriting quality varies and no provider should be selected permanently based only on public benchmarks.

## Provider interface

Conceptual Python types:

```python
@dataclass
class OCRContext:
    event_type: str | None
    expected_types: tuple[str, ...] = ("EMPLOYER", "QUESTION", "UNKNOWN")

@dataclass
class OCRResult:
    raw_text: str
    suggested_type: str
    confidence: float | None
    provider: str
    model: str | None
    metadata: dict

class OCRProvider(Protocol):
    async def extract(self, image: bytes, context: OCRContext) -> OCRResult:
        ...
```

Provider-specific exceptions must map to application-level errors.

## Required adapters

### Mock provider

Implement first.

Purpose:

- deterministic frontend/backend development,
- CI,
- no GPU/API dependency,
- easy error/low-confidence test fixtures.

### HunyuanOCR provider

Primary open-source/local candidate.

Keep it isolated from core API code because its runtime/GPU requirements may differ substantially from the main FastAPI environment.

Preferred designs:

A. Separate local OCR HTTP service/container.
B. Separate Python process/service on host if container GPU integration is temporarily harder.

Do not force Hunyuan packages into the main API environment.

Current local implementation:

- llama.cpp runs as a separate process on `127.0.0.1:8081`
- the Q8 GGUF language model and multimodal projector are loaded from ignored workspace storage
- FastAPI calls the OpenAI-compatible `/v1/chat/completions` endpoint through the provider interface
- the provider never falls back to a cloud endpoint
- API readiness and the capture UI expose model availability
- OpenCV sends a normalized response-area crop while retaining the full normalized card only until approval

The current official HunyuanOCR-1.5 inference documentation should be re-checked during implementation. As of this handoff, the official guide describes a unified environment and CUDA requirements that may require explicit driver/runtime validation.

Codex must:

- inspect `nvidia-smi`,
- inspect installed NVIDIA container/runtime support,
- verify current official HunyuanOCR inference instructions,
- avoid upgrading drivers/CUDA system-wide without explicit approval.

### Extend provider

Cloud/document-processing benchmark candidate.

Use structured extraction with a schema conceptually equivalent to:

```json
{
  "text": "string",
  "type": "EMPLOYER | QUESTION | UNKNOWN"
}
```

Cloud use for real student data is opt-in only.

Never put `EXTEND_API_KEY` in source control.

## Classification strategy

Provider should ideally return text + suggested class.

Add a conservative validation layer:

Question indicators may include:

- terminal `?`
- common question starters such as what/why/how/who/when/where/which/would/can/do/is/are

However, heuristics are secondary and must not override a confident provider result blindly.

When ambiguous, return `UNKNOWN`.

The operator has final authority.

## Confidence

Different OCR providers expose different confidence semantics.

Rules:

- confidence may be nullable,
- never compare provider confidence scores as if calibrated identically,
- low confidence should visually encourage review,
- human approval is required regardless of confidence.

## Prompting/extraction goal

The model should be instructed to focus on handwritten content in the response area and ignore printed branding.

Output should preserve student wording rather than "improve" it.

Do not silently grammar-correct or rewrite the student's response.

Examples:

Image handwriting:
`Fox Sports`

Result:
```json
{
  "raw_text": "Fox Sports",
  "suggested_type": "EMPLOYER"
}
```

Image handwriting:
`what makes a potential employee stand out?`

Result should preserve content; capitalization may reflect faithful OCR, not editorial rewriting.

## OCR retries

Each retry creates an `ocr_attempts` row.

A retry can:

- use same provider after improved crop,
- use a different preprocessing variant,
- use a different OCR provider.

The UI may choose a retry result as the new raw/current OCR suggestion, but old attempts remain available for diagnostics.

## Benchmark before final provider lock-in

Use a labeled set of real card styles after confirming data-use/privacy requirements.

Compare at minimum:

- transcription accuracy
- perfect-card rate
- manual correction rate
- type classification accuracy
- latency
- failure rate
- GPU/resource cost
- privacy/deployment implications

Do not choose provider solely by generic OCR benchmark rank.
