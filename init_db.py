from sqlalchemy import inspect
from alembic import command
from alembic.config import Config

from db import engine, Base
import models  # registers all the tables on Base

cfg = Config("alembic.ini")

if "alembic_version" not in inspect(engine).get_table_names():
    # brand-new database: build every table from the models, then mark it as up to date
    Base.metadata.create_all(engine)
    command.stamp(cfg, "head")
    print("New database: tables created and stamped at the latest migration")
else:
    # existing database: apply any migrations it hasn't had yet
    command.upgrade(cfg, "head")