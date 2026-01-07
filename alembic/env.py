import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from pisag.config import get_config  # noqa: E402
from pisag.models import Base, Message, MessageRecipient, Pager, SystemConfig, TransmissionLog  # noqa: E402,F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _get_url() -> str:
    env_path = os.getenv("ALEMBIC_DB_PATH")
    if env_path:
        return f"sqlite:///{env_path}"

    ini_url = config.get_main_option("sqlalchemy.url")
    if ini_url:
        return ini_url

    cfg = get_config()
    db_path = cfg.get("system", {}).get("database_path", "pisag.db")
    return f"sqlite:///{db_path}"


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=_get_url(),
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
