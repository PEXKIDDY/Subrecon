"""Aggregate all ORM models so Base.metadata sees every table."""
from app.models.user import AuditLog, User, UserRole
from app.models.project import (
    Notification,
    NotificationChannel,
    Project,
    Scan,
    ScanHistory,
    ScanStatus,
)
from app.models.asset import (
    ApiEndpoint,
    Asset,
    Certificate,
    CrawlResult,
    DnsRecord,
    Port,
    Screenshot,
    Takeover,
    Technology,
    WaybackUrl,
)

__all__ = [
    "User",
    "UserRole",
    "AuditLog",
    "Project",
    "Scan",
    "ScanStatus",
    "ScanHistory",
    "Notification",
    "NotificationChannel",
    "Asset",
    "DnsRecord",
    "Port",
    "Technology",
    "Screenshot",
    "Certificate",
    "WaybackUrl",
    "CrawlResult",
    "ApiEndpoint",
    "Takeover",
]
