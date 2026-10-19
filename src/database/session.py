import os 

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

from src.config.api_settings import PROJECT_ROOT

# 1. Resolve the database file location.
def resolve_job_database_path() -> Path:
    """
    Resolve the SQLite database path relative to 
    the project root when a relative path is used.
    """

    configured_path = os.environ.get(
        "CASTLE_JOB_DB_PATH",
        "data/jobs/jobs.sqlite3",
    )

    database_path = Path(configured_path).expanduser()

    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path

    return database_path.resolve()

# 2. Prepare the database directory.
DATABASE_PATH = resolve_job_database_path()

DATABASE_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

# 3. Create the SQLALchemy engine.
engine = create_engine(
    URL.create(
        "sqlite+pysqlite",
        database=str(DATABASE_PATH),
    ),
    connect_args={
        "check_same_thread": False,
        "timeout": 30,
    },
)

# 4. Define the session factory.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

# 5. Provide a session dependency.
def get_db_session() -> Iterator[Session]:
    """
    Yield a database session and close it
    when the operation finishes.
    """

    with SessionLocal() as session:
        yield session