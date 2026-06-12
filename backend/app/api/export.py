"""Asset export in CSV / JSON / XLSX / PDF."""
from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.database import get_db
from app.models import Asset, User

router = APIRouter(tags=["export"])

_FIELDS = ["hostname", "ip", "asn", "asn_org", "cdn", "is_live", "status_code",
           "title", "server", "level", "source"]


def _rows(db: Session, project_id: int | None):
    q = db.query(Asset).options(selectinload(Asset.technologies))
    if project_id:
        q = q.filter(Asset.project_id == project_id)
    return q.order_by(Asset.hostname).all()


def _as_dict(a: Asset) -> dict:
    d = {f: getattr(a, f) for f in _FIELDS}
    d["technologies"] = ", ".join(t.name for t in a.technologies)
    return d


@router.get("/export")
def export_assets(fmt: str = Query("csv", pattern="^(csv|json|xlsx|pdf)$"),
                  project_id: int | None = None, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    assets = _rows(db, project_id)
    data = [_as_dict(a) for a in assets]

    if fmt == "json":
        return Response(json.dumps(data, default=str, indent=2),
                        media_type="application/json",
                        headers={"Content-Disposition": "attachment; filename=subreco_assets.json"})

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_FIELDS + ["technologies"])
        writer.writeheader()
        writer.writerows(data)
        return Response(buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=subreco_assets.csv"})

    if fmt == "xlsx":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Assets"
        headers = _FIELDS + ["technologies"]
        ws.append(headers)
        for row in data:
            ws.append([str(row.get(h, "")) for h in headers])
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return StreamingResponse(
            out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=subreco_assets.xlsx"})

    # pdf
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = [Paragraph("SUBRECO — Asset Report", styles["Title"])]
    table_data = [["Hostname", "IP", "Live", "Status", "Title"]]
    for row in data[:500]:
        table_data.append([row["hostname"], row["ip"] or "", "Y" if row["is_live"] else "N",
                           str(row["status_code"] or ""), (row["title"] or "")[:40]])
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0ea5e9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
    ]))
    elements.append(table)
    doc.build(elements)
    out.seek(0)
    return StreamingResponse(out, media_type="application/pdf",
                             headers={"Content-Disposition": "attachment; filename=subreco_assets.pdf"})
