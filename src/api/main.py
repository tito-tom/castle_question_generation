from fastapi import FastAPI
from src.api.routers import health, analyses, annotations, jobs, questions, qa, videos


def create_app() -> FastAPI:
    """
    Create and configure the CASTLE QA Studio API.
    """

    app = FastAPI(
        title="CASTLE QA Studio API.",
        description=(
            "REST API for CASTLE video understanding "
            "and question generation."
        ),
        version="0.1.0",
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

    # New asynchronous GPU job routes
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