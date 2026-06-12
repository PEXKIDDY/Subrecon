"""Assets and all associated recon-result tables."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Asset(Base):
    """A discovered host (subdomain) and its enriched HTTP/network metadata."""

    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("project_id", "hostname", name="uq_asset_project_host"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id", ondelete="SET NULL"), index=True)

    hostname: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64), index=True)
    cname: Mapped[str | None] = mapped_column(String(512))
    asn: Mapped[str | None] = mapped_column(String(64))
    asn_org: Mapped[str | None] = mapped_column(String(255))
    cdn: Mapped[str | None] = mapped_column(String(128))
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status_code: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(512))
    server: Mapped[str | None] = mapped_column(String(255))
    scheme: Mapped[str | None] = mapped_column(String(16))
    content_length: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(255))  # which tool(s) found it
    level: Mapped[int] = mapped_column(Integer, default=2)  # subdomain depth (3rd/4th level...)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped["Project"] = relationship(back_populates="assets")  # noqa: F821
    ports: Mapped[list["Port"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    technologies: Mapped[list["Technology"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    dns_records: Mapped[list["DnsRecord"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    screenshot: Mapped["Screenshot"] = relationship(back_populates="asset", uselist=False, cascade="all, delete-orphan")
    takeover: Mapped["Takeover"] = relationship(back_populates="asset", uselist=False, cascade="all, delete-orphan")


class DnsRecord(Base):
    __tablename__ = "dns_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    record_type: Mapped[str] = mapped_column(String(16), index=True)  # A, AAAA, CNAME, MX, TXT, NS...
    value: Mapped[str] = mapped_column(String(1024))
    ttl: Mapped[int | None] = mapped_column(Integer)

    asset: Mapped["Asset"] = relationship(back_populates="dns_records")


class Port(Base):
    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    port: Mapped[int] = mapped_column(Integer, index=True)
    protocol: Mapped[str] = mapped_column(String(8), default="tcp")
    service: Mapped[str | None] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16), default="open")

    asset: Mapped["Asset"] = relationship(back_populates="ports")


class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(64))

    asset: Mapped["Asset"] = relationship(back_populates="technologies")


class Screenshot(Base):
    __tablename__ = "screenshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True, unique=True)
    path: Mapped[str] = mapped_column(String(1024))  # path or URL to PNG
    url: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="screenshot")


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    subject: Mapped[str | None] = mapped_column(String(512))
    issuer: Mapped[str | None] = mapped_column(String(512))
    sans: Mapped[list | None] = mapped_column(JSON, default=list)
    not_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    not_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    serial: Mapped[str | None] = mapped_column(String(128))
    sha256: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str | None] = mapped_column(String(64))  # crt.sh, tls...


class WaybackUrl(Base):
    __tablename__ = "wayback_urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    params: Mapped[list | None] = mapped_column(JSON, default=list)
    category: Mapped[str | None] = mapped_column(String(32), index=True)  # admin, login, api, backup, other
    source: Mapped[str | None] = mapped_column(String(32))  # wayback, gau
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrawlResult(Base):
    __tablename__ = "crawl_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    is_js: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status_code: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str | None] = mapped_column(String(32))  # katana
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(String(8))
    source_js: Mapped[str | None] = mapped_column(Text)  # JS file it was extracted from
    secret_type: Mapped[str | None] = mapped_column(String(64))  # populated if a secret/key found
    secret_match: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Takeover(Base):
    __tablename__ = "takeovers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True, unique=True)
    service: Mapped[str] = mapped_column(String(64))
    cname: Mapped[str | None] = mapped_column(String(512))
    confidence: Mapped[str] = mapped_column(String(16), default="low")  # low|medium|high
    risk_level: Mapped[str] = mapped_column(String(16), default="medium")
    evidence: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="takeover")
