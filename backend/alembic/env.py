"""Read private application settings; never put credentials in alembic.ini."""

from alembic import context

from app.core.config import load_settings
from app.core.database import Database
from app.models.metric import Base


def run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


provided_connection = context.config.attributes.get("connection")
if provided_connection is not None:
    # Integration tests supply their disposable database connection explicitly.
    run_migrations(provided_connection)
else:
    database = Database(load_settings())
    if database.engine is None:
        raise RuntimeError("Configure database credentials before running migrations.")
    try:
        if context.is_offline_mode():
            context.configure(
                url=database.engine.url,
                target_metadata=Base.metadata,
                literal_binds=True,
                dialect_opts={"paramstyle": "named"},
            )
            with context.begin_transaction():
                context.run_migrations()
        else:
            with database.engine.connect() as connection:
                run_migrations(connection)
    finally:
        database.engine.dispose()
