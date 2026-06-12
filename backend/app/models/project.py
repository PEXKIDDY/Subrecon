"""Projects (a target/program), scans, scan history, and notifications."""
import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationChannel(str, enum.Enum):
    DISCORD = "discord"
    TELEGRAM = "telegram"
    SLACK = "slack"
    EMAIL = "email"
    INAPP = "inapp"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="projects")  # noqa: F821
    scans: Mapped[list["Scan"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    assets: Mapped[list["Asset"]] = relationship(back_populates="project", cascade="all, delete-orphan")  # noqa: F821


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    status: Mapped[ScanStatus] = mapped_column(Enum(ScanStatus), default=ScanStatus.QUEUED, index=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    current_stage: Mapped[str | None] = mapped_column(String(128))
    config: Mapped[dict | None] = mapped_column(JSON, default=dict)
    stats: Mapped[dict | None] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="scans")
    history: Mapped[list["ScanHistory"]] = relationship(back_populates="scan", cascade="all, delete-orphan")


class ScanHistory(Base):
    """Per-stage event log for a scan (used for the live timeline)."""

    __tablename__ = "scan_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("scans.id", ondelete="CASCADE"), index=True)
    stage: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(16), default="info")  # info|warn|error
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    scan: Mapped["Scan"] = relationship(back_populates="history")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel), default=NotificationChannel.INAPP)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), default="info")
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
