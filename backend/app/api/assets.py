"""Asset Explorer endpoints: search, sort, filter, paginate."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Asset, User
from app.schemas import AssetOut, Paginated

router = APIRouter(tags=["assets"])

_SORTABLE = {
    "hostname": Asset.hostname, "ip": Asset.ip, "status_code": Asset.status_code,
    "is_live": Asset.is_live, "last_seen": Asset.last_seen, "level": Asset.level,
}


@router.get("/assets", response_model=Paginated)
def list_assets(
    project_id: int | None = None,
    search: str | None = None,
    is_live: bool | None = None,
    cdn: str | None = None,
    sort_by: str = Query("last_seen"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Asset).options(selectinload(Asset.ports), selectinload(Asset.technologies))
    if project_id:
        q = q.filter(Asset.project_id == project_id)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Asset.hostname.ilike(like), Asset.ip.ilike(like),
                         Asset.title.ilike(like), Asset.server.ilike(like)))
    if is_live is not None:
        q = q.filter(Asset.is_live.is_(is_live))
    if cdn:
        q = q.filter(Asset.cdn.ilike(f"%{cdn}%"))

    total = q.count()
    col = _SORTABLE.get(sort_by, Asset.last_seen)
    q = q.order_by(col.asc() if order == "asc" else col.desc())
    rows = q.offset((page - 1) * page_size).limit(page_size).all()

    return Paginated(
        total=total, page=page, page_size=page_size,
        items=[AssetOut.model_validate(r).model_dump() for r in rows],
    )


@router.get("/assets/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    asset = (db.query(Asset).options(selectinload(Asset.ports), selectinload(Asset.technologies))
             .filter(Asset.id == asset_id).first())
    if not asset:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset
