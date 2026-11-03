"""Database connection and SQLAlchemy model base."""

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase

database_url = make_url(
    os.environ["DATABASE_URL"]
).set(drivername="postgresql+psycopg")

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)


class Base(DeclarativeBase):
    """Base class for the application's database models."""