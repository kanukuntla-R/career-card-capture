import base64
import json
import re

import httpx

from app.services.ocr.classification import classify_text
from app.services.ocr.types import (
    OCRContext,
    OCRProviderError,
    OCRProviderStatus,
    OCRResult,
)

OCR_PROMPT = (
    "Extract only the handwritten response from the light or white response area of this "
    "career-services card. Ignore printed branding, borders, guide text, and the dark branded "
    "strip. Preserve the writer's exact spelling, capitalization, and punctuation. Return only "
    "the response text, with no explanation, label, Markdown, or quotation marks."
)


class HunyuanOCRProvider:
    provider_id = "hunyuan"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        normalized_url = base_url.rstrip("/")
        self.base_url = normalized_url if normalized_url.endswith("/v1") else f"{normalized_url}/v1"
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def health(self) -> OCRProviderStatus:
        try:
            async with httpx.AsyncClient(timeout=3.0, transport=self.transport) as client:
                response = await client.get(f"{self.base_url}/models")
                response.raise_for_status()
            return OCRProviderStatus(
                provider_id=self.provider_id,
                enabled=True,
                ready=True,
                model=self.model,
            )
        except (httpx.HTTPError, ValueError):
            return OCRProviderStatus(
                provider_id=self.provider_id,
                enabled=True,
                ready=False,
                model=self.model,
                detail="Local HunyuanOCR server is not ready.",
            )

    async def extract(self, image: bytes, context: OCRContext) -> OCRResult:
        del context
        encoded = base64.b64encode(image).decode("ascii")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a faithful OCR engine."},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                        },
                        {"type": "text", "text": OCR_PROMPT},
                    ],
                },
            ],
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 256,
            "repeat_penalty": 1.08,
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, transport=self.transport
            ) as client:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload)
                response.raise_for_status()
                body = response.json()
            content = body["choices"][0]["message"]["content"]
            text = self._clean_text(content)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise OCRProviderError("Local HunyuanOCR could not process the card.") from exc

        if not text:
            raise OCRProviderError("Local HunyuanOCR returned an empty transcription.")
        return OCRResult(
            raw_text=text,
            suggested_type=classify_text(text),
            confidence=None,
            provider=self.provider_id,
            model=self.model,
            metadata={"backend": "llama.cpp", "local_only": True},
        )

    @staticmethod
    def _clean_text(content: object) -> str:
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not isinstance(content, str):
            return ""
        text = content.strip()
        text = re.sub(r"^```(?:text|markdown|json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()
        if text.startswith("{"):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and isinstance(parsed.get("text"), str):
                    text = parsed["text"].strip()
            except json.JSONDecodeError:
                pass
        prefixes = ("Transcription:", "Response:", "Text:")
        for prefix in prefixes:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix) :].strip()
                break
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
            text = text[1:-1].strip()
        return text
