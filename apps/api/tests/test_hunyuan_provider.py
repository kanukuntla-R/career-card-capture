import json

import httpx
import pytest

from app.services.ocr import HunyuanOCRProvider, OCRContext


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_hunyuan_openai_compatible_request_and_cleanup() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "HYVL"}]})
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Response: Fox Sports"}}]},
        )

    provider = HunyuanOCRProvider(
        "http://ocr.test:8081/v1",
        "HYVL",
        transport=httpx.MockTransport(handler),
    )

    status = await provider.health()
    result = await provider.extract(b"jpeg bytes", OCRContext(event_type="TABLING"))

    assert status.ready is True
    assert captured["model"] == "HYVL"
    assert captured["messages"][1]["content"][0]["image_url"]["url"].startswith(
        "data:image/jpeg;base64,"
    )
    assert result.raw_text == "Fox Sports"
    assert result.suggested_type == "EMPLOYER"
    assert result.provider == "hunyuan"
