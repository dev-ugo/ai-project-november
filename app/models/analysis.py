"""Database model for a CSV analysis report."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Analysis(Base):
    """Store an analysis summary and its detailed anomalies."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    row_count: Mapped[int] = mapped_column(default=0)
    duplicate_count: Mapped[int] = mapped_column(default=0)
    empty_cell_count: Mapped[int] = mapped_column(default=0)

    anomalies: Mapped[list[dict]] = mapped_column(JSON, default=list)

    # Les anciens rapports restent sans propriétaire et ne sont jamais publics.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    corrected_csv: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
    correction_key: Mapped[str | None] = mapped_column(String(36), default=lambda: str(uuid4()))
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
