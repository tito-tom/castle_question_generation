
import os
import sqlite3

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_database_path() -> Path:
    configured = os.environ.get(
        "CASTLE_JOB_DB_PATH",
        "data/jobs/jobs.sqlite3",
    )

    path = Path(configured).expanduser()

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def main() -> None:
    database_path = get_database_path()

    print("Database:", database_path)

    if not database_path.exists():
        print("[INFO] No existing database found.")
        print("An initial Alembic upgrade will be needed.")
        return

    if not database_path.is_file():
        raise RuntimeError(
            "Database path is not a regular file"
        )

    # Create a unique backup name.
    backup_directory = (
        database_path.parent / "backups"
    )

    backup_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")

    backup_path = backup_directory / (
        f"{database_path.stem}_before_alembic_"
        f"{timestamp}_{uuid4().hex[:8]}.sqlite3"
    )

    # Use SQLite's backup API, rather than
    # copying the database file directly.
    with closing(
        sqlite3.connect(
            database_path.as_uri() + "?mode=ro",
            uri=True,
        )
    ) as source:
        with closing(
            sqlite3.connect(str(backup_path))
        ) as destination:
            source.backup(destination)

    print("[PASS] Backup created:", backup_path)

    # Inspect the backup only.
    with closing(
        sqlite3.connect(
            backup_path.as_uri() + "?mode=ro",
            uri=True,
        )
    ) as connection:

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise RuntimeError(
                f"Backup integrity check failed: {integrity}"
            )

        print("[PASS] Backup integrity check")

        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

        print("Tables:", sorted(tables))

        if "inference_jobs" not in tables:
            print("[INFO] inference_jobs table absent")
            print("Do not stamp this database.")
            return

        print("[PASS] inference_jobs table exists")

        print("\nColumns:")
        columns = connection.execute(
            "PRAGMA table_info('inference_jobs')"
        ).fetchall()

        for column in columns:
            print(
                f"  {column[1]}: {column[2]} "
                f"(notnull={column[3]}, pk={column[5]})"
            )

        print("\nQueue index:")
        indexes = connection.execute(
            "PRAGMA index_info('idx_inference_jobs_queue')"
        ).fetchall()

        print([row[2] for row in indexes])

        job_count = connection.execute(
            "SELECT COUNT(*) FROM inference_jobs"
        ).fetchone()[0]

        print("\nSaved jobs:", job_count)

        if "alembic_version" in tables:
            revisions = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchall()

            print(
                "Alembic revisions:",
                [row[0] for row in revisions],
            )
        else:
            print("Alembic version: Not initialized")

    print("\nDatabase audit completed successfully.")


if __name__ == "__main__":
    main()
