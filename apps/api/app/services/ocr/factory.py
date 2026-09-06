from app.core.config import Settings
from app.services.ocr.hunyuan import HunyuanOCRProvider
from app.services.ocr.mock import MockOCRProvider
from app.services.ocr.types import OCRProvider


def build_ocr_provider(settings: Settings) -> OCRProvider:
    provider_id = settings.ocr_provider.strip().lower()
    if provider_id == "mock":
        return MockOCRProvider()
    if provider_id == "hunyuan":
        return HunyuanOCRProvider(
            base_url=settings.hunyuan_ocr_base_url,
            model=settings.hunyuan_model_name,
            timeout_seconds=settings.hunyuan_request_timeout_seconds,
        )
    raise ValueError(f"Unsupported OCR provider: {settings.ocr_provider}")
