# Architecture & Extension Guide

This document explains how SUBRECO is put together and exactly where to extend it.

---

## Request & scan lifecycle

1. The UI calls `POST /api/scan` with a root domain.
2. The API validates the domain, reuses or creates a **Project**, creates a **Scan**
   (status `QUEUED`), and dispatches a Celery task `run_scan(scan_id, project_id, domain)`.
3. The worker runs `ReconOrchestrator.run()`, which executes stages in order. After each
   stage it:
   - persists results to Postgres,
   - writes a `ScanHistory` row,
   - publishes a progress event to Redis (`subreco:events`).
4. The API subscribes to that Redis channel and fans events out to any WebSocket clients
   connected at `/ws/scans/{scan_id}` — that's the live progress you see.
5. On completion the scan is marked `COMPLETED` (or `FAILED`) and notifications fire.

---

## Backend layout

```
backend/app/
├── main.py            FastAPI app, CORS, routers, WebSocket, lifespan
├── config.py          Pydantic settings (env-driven)
├── database.py        Engine, SessionLocal, Base, get_db, init_db
├── celery_app.py      Celery instance
├── tasks.py           run_scan task (drives orchestrator + progress)
├── ws.py              ConnectionManager, Redis listener, publish_event
├── notifications.py   Discord/Slack/Telegram/Email senders
├── schemas.py         Pydantic v2 request/response models
├── core/security.py   bcrypt + JWT
├── api/               Route modules: auth, scans, assets, intel, export, deps
├── models/            SQLAlchemy models: user, project, asset
└── recon/
    ├── runner.py        tool_available(), run_tool() subprocess wrapper
    ├── passive.py       crt.sh, OTX, RapidDNS, BufferOver, SecurityTrails
    ├── tools.py         binary wrappers (subfinder, httpx, naabu, katana, …)
    ├── dnsutil.py       pure-Python DNS fallback (dnspython)
    ├── takeover.py      CNAME fingerprints + detection
    ├── js_intel.py      URL categorization + secret patterns
    └── orchestrator.py  ReconOrchestrator — the pipeline
```

---

## Data model (core tables)

- **User / AuditLog** — accounts (ADMIN/ANALYST/VIEWER) and an audit trail.
- **Project** — one root domain; everything hangs off this.
- **Scan / ScanHistory** — a run and its per-stage event log.
- **Asset** — a discovered host (ip, cname, asn, cdn, is_live, status_code, title,
  server, level, source). Unique per `(project, hostname)`.
- **DnsRecord, Port, Technology, Screenshot, Certificate** — per-asset detail.
- **WaybackUrl, CrawlResult, ApiEndpoint** — URL/JS intelligence (with secret fields).
- **Takeover** — a flagged dangling-CNAME candidate with confidence + risk.
- **Notification** — record of an outbound alert.

---

## The orchestrator

`ReconOrchestrator` defines `STAGES` as an ordered list, each with a cumulative progress
percentage. Each stage is **fault-isolated**: an exception in one stage is logged and the
pipeline continues. Stages call into `recon/` helpers and persist as they go.

### Graceful degradation

Tool-based stages call `tool_available(name)` (a cached `shutil.which`). If the binary is
missing, the stage logs "skipped — <tool> not installed" and returns empty, so a minimal
install still produces results from the passive HTTP sources.

---

## How to extend a stage

### Add a new passive source

1. Add a function in `recon/passive.py` that returns a set of hostnames, e.g.:
   ```python
   async def from_mysource(domain: str, client: httpx.AsyncClient) -> set[str]:
       r = await client.get(f"https://api.mysource.test/subs/{domain}")
       return _clean(domain, r.json().get("subdomains", []))
   ```
2. Call it inside `collect_passive()` alongside the others.
3. Done — `_clean()` already normalizes and scope-checks results.

### Add a new tool wrapper

1. Add a wrapper in `recon/tools.py` using `run_tool([...])` from `runner.py`.
   `run_tool` never raises, respects a timeout, and returns stdout safely.
2. Call it from the relevant stage in `orchestrator.py`, guarded by `tool_available(...)`.

### Add a new takeover fingerprint

Append to `FINGERPRINTS` in `recon/takeover.py`:
```python
{"service": "MyService", "cname": "myservice.io",
 "body": "no such app", "risk": "high"}
```

### Wire up Certificate intelligence (documented extension point)

The `Certificate` model exists and crt.sh is already queried for subdomains. To populate
certificates:

1. In `recon/passive.py`, capture the full crt.sh JSON (issuer, not_before, not_after,
   name_value) instead of only hostnames.
2. Add a `stage_certificates` method to `ReconOrchestrator` that maps those rows to
   `Certificate(asset_id=…, issuer=…, valid_from=…, valid_to=…, sans=…)`.
3. Insert the stage into `STAGES` with an appropriate progress weight.
4. Surface it via a `/api/certificates` route (the intel router already has the pattern).

The frontend has no dedicated certificate page yet — the **Wayback & JS** and **Takeover**
pages show the established pattern (`useAuthGuard` + `api.*` + table/cards) to copy.

---

## Frontend layout

```
frontend/
├── app/
│   ├── layout.tsx         Root shell + sidebar + fonts
│   ├── globals.css        Theme tokens + signature scanline
│   ├── login/page.tsx     Auth
│   ├── page.tsx           Dashboard (launcher, stats, charts, export)
│   ├── assets/page.tsx    Asset Explorer (TanStack Table, search/filter/sort/paginate)
│   ├── scans/page.tsx     Scan history + stage timeline
│   ├── dns/page.tsx       DNS & ports
│   ├── screenshots/…      Screenshot gallery
│   ├── takeovers/…        Takeover center
│   ├── wayback/…          Wayback URLs + JS secrets
│   ├── projects/…         Projects + rescan
│   └── notifications/…    Channel status
├── components/            Sidebar, ui primitives, ScanLauncher, Charts
└── lib/api.ts             Typed API client + scanSocket()
```

### Adding a page

1. Add a route under `app/<name>/page.tsx`. Start it with `useAuthGuard()`.
2. Add a method to `lib/api.ts` if you need a new endpoint.
3. Add the link to `NAV` in `components/Sidebar.tsx`.
4. Reuse `PageHeader`, `StatTile`, `Badge`, `Spinner`, `EmptyState` from `components/ui.tsx`
   to stay on-theme.

---

## Design language

The UI is a deliberate "recon console": an ink-navy base (not pure black), a signature
animated **scanline** marking active/live surfaces, a monospace data face for all machine
output, and status accents (live green, risk red, warn amber, scan cyan). Tokens live in
`tailwind.config.js` and `globals.css`. Keep the boldness in the scanline; keep everything
else quiet.
