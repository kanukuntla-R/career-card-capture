from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class OCRContext:
    event_type: str | None
    expected_types: tuple[str, ...] = ("EMPLOYER", "QUESTION", "UNKNOWN")
    fixture_text: str | None = None


@dataclass(frozen=True)
class OCRResult:
    raw_text: str
    suggested_type: str
    confidence: float | None
    provider: str
    model: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OCRProviderStatus:
    provider_id: str
    enabled: bool
    ready: bool
    model: str | None = None
    detail: str | None = None


class OCRProviderError(RuntimeError):
    """Safe application-level OCR failure."""


class OCRProvider(Protocol):
    provider_id: str

    async def extract(self, image: bytes, context: OCRContext) -> OCRResult: ...

    async def health(self) -> OCRProviderStatus: ...
