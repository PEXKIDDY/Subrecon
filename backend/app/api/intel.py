"""Dashboard aggregates and intelligence endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models import (
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
from app.models import User
from app.schemas import DashboardStats

router = APIRouter(tags=["intel"])


def _project_filter(model, project_id):
    return [model.project_id == project_id] if project_id else []


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(project_id: int | None = None, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    af = _project_filter(Asset, project_id)
    asset_ids = db.query(Asset.id).filter(*af)
    return DashboardStats(
        total_assets=db.query(Asset).filter(*af).count(),
        live_hosts=db.query(Asset).filter(*af, Asset.is_live.is_(True)).count(),
        dead_hosts=db.query(Asset).filter(*af, Asset.is_live.is_(False)).count(),
        open_ports=db.query(Port).filter(Port.asset_id.in_(asset_ids)).count(),
        technologies=db.query(Technology).filter(Technology.asset_id.in_(asset_ids)).count(),
        screenshots=db.query(Screenshot).filter(Screenshot.asset_id.in_(asset_ids)).count(),
        dns_records=db.query(DnsRecord).filter(DnsRecord.asset_id.in_(asset_ids)).count(),
        wayback_urls=db.query(WaybackUrl).filter(*_project_filter(WaybackUrl, project_id)).count(),
        api_endpoints=db.query(ApiEndpoint).filter(*_project_filter(ApiEndpoint, project_id)).count(),
        js_files=db.query(CrawlResult).filter(*_project_filter(CrawlResult, project_id),
                                              CrawlResult.is_js.is_(True)).count(),
        takeovers=db.query(Takeover).filter(Takeover.asset_id.in_(asset_ids)).count(),
    )


@router.get("/dashboard/charts")
def dashboard_charts(project_id: int | None = None, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    af = _project_filter(Asset, project_id)
    asset_ids = db.query(Asset.id).filter(*af)

    def grouped(query):
        return [{"name": str(k) if k is not None else "unknown", "value": v} for k, v in query]

    live = db.query(Asset).filter(*af, Asset.is_live.is_(True)).count()
    dead = db.query(Asset).filter(*af, Asset.is_live.is_(False)).count()

    tech = grouped(db.query(Technology.name, func.count(Technology.id))
                   .filter(Technology.asset_id.in_(asset_ids))
                   .group_by(Technology.name).order_by(func.count(Technology.id).desc()).limit(10))
    asn = grouped(db.query(Asset.asn_org, func.count(Asset.id)).filter(*af, Asset.asn_org.isnot(None))
                  .group_by(Asset.asn_org).order_by(func.count(Asset.id).desc()).limit(10))
    ports = grouped(db.query(Port.port, func.count(Port.id)).filter(Port.asset_id.in_(asset_ids))
                    .group_by(Port.port).order_by(func.count(Port.id).desc()).limit(10))
    dns = grouped(db.query(DnsRecord.record_type, func.count(DnsRecord.id))
                  .filter(DnsRecord.asset_id.in_(asset_ids)).group_by(DnsRecord.record_type))

    return {
        "live_vs_dead": [{"name": "Live", "value": live}, {"name": "Dead", "value": dead}],
        "technology_distribution": tech,
        "asn_distribution": asn,
        "port_distribution": ports,
        "dns_distribution": dns,
    }


@router.get("/dns")
def list_dns(project_id: int | None = None, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    af = _project_filter(Asset, project_id)
    asset_ids = db.query(Asset.id).filter(*af)
    rows = (db.query(DnsRecord, Asset.hostname).join(Asset)
            .filter(DnsRecord.asset_id.in_(asset_ids)).limit(2000).all())
    return [{"hostname": h, "type": r.record_type, "value": r.value, "ttl": r.ttl} for r, h in rows]


@router.get("/ports")
def list_ports(project_id: int | None = None, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    af = _project_filter(Asset, project_id)
    asset_ids = db.query(Asset.id).filter(*af)
    rows = (db.query(Port, Asset.hostname).join(Asset)
            .filter(Port.asset_id.in_(asset_ids)).all())
    return [{"hostname": h, "port": p.port, "protocol": p.protocol, "service": p.service,
             "state": p.state} for p, h in rows]


@router.get("/wayback")
def list_wayback(project_id: int | None = None, category: str | None = None,
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(WaybackUrl).filter(*_project_filter(WaybackUrl, project_id))
    if category:
        q = q.filter(WaybackUrl.category == category)
    rows = q.limit(2000).all()
    return [{"url": r.url, "params": r.params, "category": r.category, "source": r.source} for r in rows]


@router.get("/endpoints")
def list_endpoints(project_id: int | None = None, secrets_only: bool = False,
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(ApiEndpoint).filter(*_project_filter(ApiEndpoint, project_id))
    if secrets_only:
        q = q.filter(ApiEndpoint.secret_type.isnot(None))
    rows = q.limit(2000).all()
    return [{"url": r.url, "method": r.method, "source_js": r.source_js,
             "secret_type": r.secret_type, "secret_match": r.secret_match} for r in rows]


@router.get("/certificates")
def list_certificates(project_id: int | None = None, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    rows = db.query(Certificate).filter(*_project_filter(Certificate, project_id)).limit(2000).all()
    return [{"subject": r.subject, "issuer": r.issuer, "sans": r.sans,
             "not_after": r.not_after, "sha256": r.sha256, "source": r.source} for r in rows]


@router.get("/takeovers")
def list_takeovers(project_id: int | None = None, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    af = _project_filter(Asset, project_id)
    asset_ids = db.query(Asset.id).filter(*af)
    rows = (db.query(Takeover, Asset.hostname).join(Asset)
            .filter(Takeover.asset_id.in_(asset_ids)).all())
    return [{"hostname": h, "service": t.service, "cname": t.cname, "confidence": t.confidence,
             "risk_level": t.risk_level, "evidence": t.evidence} for t, h in rows]


@router.get("/screenshots")
def list_screenshots(project_id: int | None = None, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    af = _project_filter(Asset, project_id)
    asset_ids = db.query(Asset.id).filter(*af)
    rows = (db.query(Screenshot, Asset.hostname).join(Asset)
            .filter(Screenshot.asset_id.in_(asset_ids)).all())
    return [{"hostname": h, "path": s.path, "url": s.url} for s, h in rows]
