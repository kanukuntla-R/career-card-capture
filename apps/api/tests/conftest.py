from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models import Base


@pytest.fixture
def app(tmp_path: Path):
    settings = Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        ocr_provider="mock",
        google_sheets_enabled=False,
        card_image_dir=tmp_path / "images",
        card_image_retention="delete_after_approval",
    )
    test_app = create_app(settings)
    Base.metadata.create_all(test_app.state.engine)
    yield test_app
    test_app.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client
