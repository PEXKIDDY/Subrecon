"""Pydantic v2 schemas (request/response contracts)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole
from app.models.project import ScanStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Auth / Users ----------
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.ANALYST


class UserOut(ORMModel):
    id: int
    email: EmailStr
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    username: str
    password: str


# ---------- Projects ----------
class ProjectCreate(BaseModel):
    name: str
    root_domain: str
    description: str | None = None


class ProjectOut(ORMModel):
    id: int
    name: str
    root_domain: str
    description: str | None
    owner_id: int
    created_at: datetime


# ---------- Scans ----------
class ScanCreate(BaseModel):
    domain: str = Field(..., description="Root domain, e.g. example.com")
    project_id: int | None = None
    config: dict | None = None


class ScanOut(ORMModel):
    id: int
    project_id: int
    status: ScanStatus
    progress: int
    current_stage: str | None
    stats: dict | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class ScanHistoryOut(ORMModel):
    id: int
    stage: str
    message: str | None
    level: str
    created_at: datetime


# ---------- Assets ----------
class PortOut(ORMModel):
    port: int
    protocol: str
    service: str | None
    state: str


class TechnologyOut(ORMModel):
    name: str
    version: str | None
    category: str | None


class AssetOut(ORMModel):
    id: int
    hostname: str
    ip: str | None
    cname: str | None
    asn: str | None
    asn_org: str | None
    cdn: str | None
    is_live: bool
    status_code: int | None
    title: str | None
    server: str | None
    level: int
    source: str | None
    last_seen: datetime
    ports: list[PortOut] = []
    technologies: list[TechnologyOut] = []


class DashboardStats(BaseModel):
    total_assets: int
    live_hosts: int
    dead_hosts: int
    open_ports: int
    technologies: int
    screenshots: int
    dns_records: int
    wayback_urls: int
    api_endpoints: int
    js_files: int
    takeovers: int


class Paginated(BaseModel):
    total: int
    page: int
    page_size: int
    items: list
