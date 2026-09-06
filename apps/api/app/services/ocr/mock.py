from app.services.ocr.classification import classify_text
from app.services.ocr.types import OCRContext, OCRProviderStatus, OCRResult


class MockOCRProvider:
    """Deterministic provider for the first vertical slice and automated tests."""

    provider_id = "mock"

    async def health(self) -> OCRProviderStatus:
        return OCRProviderStatus(
            provider_id=self.provider_id,
            enabled=True,
            ready=True,
            model="deterministic-v1",
        )

    async def extract(self, image: bytes, context: OCRContext) -> OCRResult:
        del image
        text = (context.fixture_text or "Fox Sports").strip()
        return OCRResult(
            raw_text=text,
            suggested_type=classify_text(text),
            confidence=0.97,
            provider=self.provider_id,
            model="deterministic-v1",
            metadata={"fixture": context.fixture_text is not None},
        )
