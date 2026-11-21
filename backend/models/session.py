"""Database model for MPC session metadata.

Private salaries, founder capability tokens, MPyC shares, and party private
keys are intentionally absent from this schema.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, BigInteger, DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for VEILBENCH's metadata-only tables."""


class SessionState(str, Enum):
    CREATED = "created"
    READY = "ready"
    COMPUTING = "computing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class BenchmarkSession(Base):
    __tablename__ = "benchmark_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    state: Mapped[str] = mapped_column(String(16), default=SessionState.CREATED.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_party_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    aggregate_sum: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    average_salary: Mapped[float | None] = mapped_column(Float, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
