import os
from contextlib import asynccontextmanager
from fastapi import FastAPI

from castle_qa.api.middleware.request_size_limit import RequestSizeLimitMiddleware
from castle_qa.api.routers import health, analyses, annotations, jobs, questions, qa, videos
from castle_qa.config.api_settings import APISettings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handling background maintenance tasks.
    Starts the periodic cleanup runner if enabled.
    """
    settings = APISettings.from_environment()
    runner = None
    # Enable background cleanup runner if configured (disabled by default in test mode)
    if os.environ.get("ENABLE_BACKGROUND_CLEANUP", "0") == "1":
        from castle_qa.services.cleanup_runner import TemporaryStorageCleanupRunner
        from castle_qa.services.temporary_session_service import TemporarySessionService
        session_svc = TemporarySessionService(
            base_dir=settings.temporary_clip_directory,
            retention_hours=settings.retention_hours,
        )
        runner = TemporaryStorageCleanupRunner(
            session_service=session_svc,
            temporary_dir=settings.temporary_clip_directory,
            interval_seconds=settings.cleanup_interval_seconds,
        )
        runner.start_background_loop()

    yield

    if runner:
        runner.stop_background_loop()


def create_app(enable_cleanup: bool = False) -> FastAPI:
    """
    Create and configure the CASTLE QA Studio API.
    """
    settings = APISettings.from_environment()

    app = FastAPI(
        title="CASTLE QA Studio API.",
        description=(
            "REST API for CASTLE video understanding "
            "and question generation."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware: Request body size enforcement before Starlette spooling
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_request_size_bytes=settings.max_request_size_bytes,
    )

    # Register API routers.
    app.include_router(
        health.router,
        prefix="/api/v1",
    )

    app.include_router(
        analyses.router,
        prefix="/api/v1",
    )

    app.include_router(
        questions.router,
        prefix="/api/v1",
    )

    # Asynchronous GPU job routes
    app.include_router(
        jobs.router,
        prefix="/api/v1",
    )

    # Video upload, streaming, and clipping
    app.include_router(
        videos.router,
        prefix="/api/v1",
    )

    # Grounded video question-answering
    app.include_router(
        qa.router,
        prefix="/api/v1",
    )

    # Annotation review and Whodunnit export
    app.include_router(
        annotations.router,
        prefix="/api/v1",
    )

    return app


app = create_app()


def run() -> None:
    """Entry point for the castle-api console script."""
    import uvicorn

    uvicorn.run("castle_qa.api.main:app", host="0.0.0.0", port=8000, reload=True)
