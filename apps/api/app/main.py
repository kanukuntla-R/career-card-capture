from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import cards_router, events_router, sessions_router, sync_router
from app.core.config import Settings, get_settings
from app.core.database import build_engine, build_session_factory
from app.services.ocr import build_ocr_provider
from app.services.sheets.sync import google_sheets_configured


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(
        title="Career Card Capture API",
        version="0.1.0",
        description="Persistent capture and review API for Career Services response cards.",
    )
    app.state.settings = app_settings
    app.state.engine = build_engine(app_settings.database_url)
    app.state.session_factory = build_session_factory(app.state.engine)
    app.state.ocr_provider = build_ocr_provider(app_settings)
    Path(app_settings.card_image_dir).mkdir(parents=True, exist_ok=True)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[app_settings.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        del request
        if isinstance(exc.detail, dict):
            error = exc.detail
        else:
            error = {"code": "HTTP_ERROR", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": error})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request contains invalid or missing fields.",
                    "details": jsonable_encoder(exc.errors()),
                }
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready():
        try:
            with app.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            ocr_status = await app.state.ocr_provider.health()
            return {
                "status": "ready",
                "database": "ready",
                "ocr": {
                    "provider": ocr_status.provider_id,
                    "ready": ocr_status.ready,
                    "detail": ocr_status.detail,
                },
                "google_sheets": {
                    "enabled": app_settings.google_sheets_enabled,
                    "configured": google_sheets_configured(app_settings),
                },
            }
        except Exception:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "database": "unavailable",
                    "ocr": {"provider": app_settings.ocr_provider, "ready": False},
                },
            )

    app.include_router(events_router)
    app.include_router(sessions_router)
    app.include_router(cards_router)
    app.include_router(sync_router)
    return app


app = create_app()
