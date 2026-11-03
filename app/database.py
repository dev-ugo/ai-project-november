"""Database connection and SQLAlchemy model base."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

engine = create_engine(
    os.environ["DATABASE_URL"],
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)


class Base(DeclarativeBase):
    """Base class for the application's database models."""