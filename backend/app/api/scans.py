"""Projects and scans: create a scan, list scans, fetch status/history."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models import Project, Scan, ScanHistory, ScanStatus, User, UserRole
from app.schemas import (
    ProjectCreate,
    ProjectOut,
    ScanCreate,
    ScanHistoryOut,
    ScanOut,
)
from app.tasks import run_scan

router = APIRouter(tags=["scans"])

_DOMAIN_RE = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")


# ---------------- Projects ----------------
@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_role(UserRole.ANALYST))):
    project = Project(
        name=payload.name, root_domain=payload.root_domain.lower(),
        description=payload.description, owner_id=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


# ---------------- Scans ----------------
@router.post("/scan", response_model=ScanOut, status_code=202)
def create_scan(payload: ScanCreate, db: Session = Depends(get_db),
                user: User = Depends(require_role(UserRole.ANALYST))):
    domain = payload.domain.strip().lower().lstrip("*.")
    if not _DOMAIN_RE.match(domain):
        raise HTTPException(status_code=422, detail="Invalid domain")

    # Reuse or create a project for this root domain.
    project_id = payload.project_id
    if project_id:
        project = db.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    else:
        project = db.query(Project).filter(Project.root_domain == domain).first()
        if not project:
            project = Project(name=domain, root_domain=domain, owner_id=user.id)
            db.add(project)
            db.commit()
            db.refresh(project)
        project_id = project.id

    scan = Scan(project_id=project_id, status=ScanStatus.QUEUED, config=payload.config or {})
    db.add(scan)
    db.commit()
    db.refresh(scan)

    task = run_scan.delay(scan.id, project_id, domain)
    scan.celery_task_id = task.id
    db.commit()
    db.refresh(scan)
    return scan


@router.get("/scans", response_model=list[ScanOut])
def list_scans(project_id: int | None = None, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    q = db.query(Scan)
    if project_id:
        q = q.filter(Scan.project_id == project_id)
    return q.order_by(Scan.created_at.desc()).limit(100).all()


@router.get("/scans/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/scans/{scan_id}/history", response_model=list[ScanHistoryOut])
def scan_history(scan_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (db.query(ScanHistory).filter(ScanHistory.scan_id == scan_id)
            .order_by(ScanHistory.created_at.asc()).all())
