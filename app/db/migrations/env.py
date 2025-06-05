from logging.config import fileConfig

from sqlalchemy import engine_from_config, create_engine
from sqlalchemy import pool

from alembic import context

# Ensure all models are imported so Base.metadata is populated
import app.db.models # Import the models module
from app.db.base import Base # Import your Base

# Explicitly iterate over models to ensure they are registered with Base.metadata
# This can help in complex setups or with circular dependencies.
for name in dir(app.db.models):
    attr = getattr(app.db.models, name)
    if isinstance(attr, type) and issubclass(attr, Base) and attr is not Base:
        # This line just accesses the attribute to ensure it's processed by Python's import machinery
        pass

from config import SQLALCHEMY_DATABASE_URL

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
# Ensure Alembic uses the URL from config.py, not just its own .ini settings for sqlalchemy.url
# This also helps if SQLALCHEMY_DATABASE_URL is dynamically set by environment for the app.
if SQLALCHEMY_DATABASE_URL:
    config.set_main_option('sqlalchemy.url', SQLALCHEMY_DATABASE_URL)
else:
    # Fallback or error if SQLALCHEMY_DATABASE_URL is not in config, 
    # though alembic.ini usually has a default for sqlalchemy.url
    pass 

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# DEBUG: Print the keys of the tables registered with Base.metadata
# print(f"DEBUG [Alembic env.py]: Tables in Base.metadata before autogenerate: {Base.metadata.tables.keys()}") # Temporarily commented out

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    print(f"DEBUG [Alembic env.py - OFFLINE]: Using URL: {url}")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Use the URL from our app's config, and enable SQL echoing
    db_url_for_engine = config.get_main_option("sqlalchemy.url") 
    print(f"DEBUG [Alembic env.py - ONLINE]: Using URL for engine: {db_url_for_engine}")
    
    connectable = create_engine(db_url_for_engine, echo=True)

    with connectable.connect() as connection:
        print(f"DEBUG [Alembic env.py - ONLINE]: Configuring context for connection: {connection}")
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            render_as_batch=True
        )
        
        print("DEBUG [Alembic env.py - ONLINE]: BEGINNING ONLINE MIGRATIONS with SQL echoing")
        try:
            with context.begin_transaction():
                context.run_migrations()
            print("DEBUG [Alembic env.py - ONLINE]: FINISHED ONLINE MIGRATIONS successfully")
        except Exception as e:
            print(f"DEBUG [Alembic env.py - ONLINE]: ERROR DURING MIGRATIONS: {e}")
            raise


if context.is_offline_mode():
    print("DEBUG [Alembic env.py]: Running in OFFLINE mode")
    run_migrations_offline()
else:
    print("DEBUG [Alembic env.py]: Running in ONLINE mode")
    run_migrations_online()
