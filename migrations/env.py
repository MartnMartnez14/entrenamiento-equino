import os
from alembic import context
from sqlalchemy import create_engine
from backend.models import Base
config = context.config
url = os.environ.get('DATABASE_URL', config.get_main_option('sqlalchemy.url'))
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(url).connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=connection.dialect.name == 'sqlite')
        with context.begin_transaction():
            context.run_migrations()
