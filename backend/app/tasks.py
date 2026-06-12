"""Celery tasks. The scan task drives the orchestrator and persists progress."""
from __future__ import annotations

from datetime import datetime, timezone

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Scan, ScanHistory, ScanStatus
from app.notifications import notify
from app.recon.orchestrator import ReconOrchestrator
from app.ws import publish_event


@celery_app.task(bind=True, name="app.tasks.run_scan")
def run_scan(self, scan_id: int, project_id: int, domain: str) -> dict:
    db = SessionLocal()
    scan = db.get(Scan, scan_id)
    if scan is None:
        db.close()
        return {"error": "scan not found"}

    scan.status = ScanStatus.RUNNING
    scan.celery_task_id = self.request.id
    scan.started_at = datetime.now(timezone.utc)
    db.commit()

    def progress(stage: str, message: str, pct: int) -> None:
        scan.current_stage = stage
        scan.progress = pct
        db.add(ScanHistory(scan_id=scan_id, stage=stage, message=message))
        db.commit()
        publish_event(scan_id, stage, message, pct)

    try:
        orchestrator = ReconOrchestrator(db, project_id, scan_id, domain, progress)
        stats = orchestrator.run()

        scan.status = ScanStatus.COMPLETED
        scan.progress = 100
        scan.stats = stats
        scan.finished_at = datetime.now(timezone.utc)
        db.commit()
        publish_event(scan_id, "completed", "Scan completed", 100, stats=stats)

        notify(
            "Scan completed",
            f"{domain}: {stats.get('total_assets', 0)} assets, "
            f"{stats.get('live_hosts', 0)} live, {stats.get('takeovers', 0)} takeovers",
            "info" if not stats.get("takeovers") else "high",
        )
        return stats
    except Exception as exc:  # noqa: BLE001
        scan.status = ScanStatus.FAILED
        scan.error = str(exc)[:2000]
        scan.finished_at = datetime.now(timezone.utc)
        db.add(ScanHistory(scan_id=scan_id, stage="error", message=str(exc)[:2000], level="error"))
        db.commit()
        publish_event(scan_id, "failed", str(exc)[:500], scan.progress or 0)
        notify("Scan failed", f"{domain}: {exc}", "high")
        raise
    finally:
        db.close()
