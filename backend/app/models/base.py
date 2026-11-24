"""Shared SQLAlchemy metadata for every model and for Alembic autogeneration."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
