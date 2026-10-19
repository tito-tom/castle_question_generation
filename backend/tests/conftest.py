"""
Shared pytest fixtures for the CASTLE QA Studio test suite.
"""

from collections.abc import Iterator
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from castle_qa.api.main import create_app
from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM
from castle_qa.infrastructure.repositories.job_repository import JobRepository


@pytest.fixture
def app():
    """Create a clean FastAPI application instance."""
    return create_app()


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    """TestClient instance for FastAPI API testing."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def temp_job_db(tmp_path: Path) -> Path:
    """Create a temporary SQLite database initialized with inference_jobs schema."""
    db_path = tmp_path / "test_jobs.sqlite3"
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(db_path)),
        poolclass=NullPool,
    )
    try:
        Base.metadata.create_all(
            engine,
            tables=[InferenceJobORM.__table__],
        )
    finally:
        engine.dispose()
    return db_path


@pytest.fixture
def job_repository(temp_job_db: Path) -> Iterator[JobRepository]:
    """Provide an isolated JobRepository backed by a temporary database."""
    repo = JobRepository(database_path=temp_job_db)
    yield repo
    repo.close()

