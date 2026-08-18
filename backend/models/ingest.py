from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class IngestArchive(Base):
    __tablename__ = "ingest_archives"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    scraper_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    b2_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FailedCeleryTask(Base):
    __tablename__ = "failed_celery_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(128), nullable=False)
    task_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    args_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retried: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
