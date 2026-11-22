"""Login credentials and assignments; never stores participant inputs."""
from sqlalchemy import String, Integer, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.models.session import Base


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("benchmark_id", "party_id"),)
    username: Mapped[str] = mapped_column(String(80), primary_key=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(256))
    invitation_hash: Mapped[str | None] = mapped_column(String(64))
    invitation_expiry: Mapped[int] = mapped_column(BigInteger, default=0)
    benchmark_id: Mapped[str | None] = mapped_column(ForeignKey("benchmark_sessions.id"))
    party_id: Mapped[int | None] = mapped_column(Integer)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[int] = mapped_column(BigInteger, default=0)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(ForeignKey("accounts.username"), nullable=False)
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
