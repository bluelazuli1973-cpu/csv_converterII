from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from flask import current_app

config = context.config

# Configure Python logging.
# Some setups (depending on how Flask-Migrate/Alembic is invoked) may provide a
# config_file_name that points to "migrations/alembic.ini" even when the real
# file lives at the project root ("alembic.ini"). Be tolerant and fall back.
if config.config_file_name:
    cfg_path = Path(config.config_file_name)

    if not cfg_path.is_file():
        # Fallback: project-root alembic.ini (one level above the migrations dir)
        root_cfg = Path(__file__).resolve().parents[1] / "alembic.ini"
        if root_cfg.is_file():
            cfg_path = root_cfg

    if cfg_path.is_file():
        fileConfig(str(cfg_path))

# Use the Flask-SQLAlchemy metadata for autogenerate
target_metadata = current_app.extensions["migrate"].db.metadata


def get_url() -> str:
    # Reads SQLALCHEMY_DATABASE_URI from Flask config
    return current_app.config.get("SQLALCHEMY_DATABASE_URI", "")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=True,  # helpful for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = current_app.extensions["migrate"].db.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,  # helpful for SQLite
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()