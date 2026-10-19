"""
Alembic migration environment for CASTLE QA Studio.

Uses the existing SQLAlchemy engine and ORM metadata.
"""

from alembic import context

from castle_qa.infrastructure.database.base import Base
from castle_qa.infrastructure.database.models.inference_job import InferenceJobORM
from castle_qa.infrastructure.database.session import engine


# Alembic configuration from alembic.ini.
config = context.config

# Importing InferenceJobORM registers its table with Base.
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """
    Generate migration SQL without opening
    a database connection.
    """
    context.configure(
        url=engine.url.render_as_string(
            hide_password=False
        ),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """
    Run migrations using the existing
    SQLAlchemy engine.
    """
    with engine.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()

# Select the execution mode.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()