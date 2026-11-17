"""Base Declarative Model untuk SQLAlchemy 2.0."""

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class untuk seluruh entity model database."""
    pass

