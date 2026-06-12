```
   ▄▄▄▄  ▄   ▄ ▄▄▄▄  ▄▄▄▄  ▄▄▄▄  ▄▄▄▄  ▄▄▄▄
   █     █   █ █   █ █   █ █     █     █   █
   ▀▀▀█  █   █ █▀▀▀▄ █▀▀▀▄ █▀▀▀  █     █   █
   ▄▄▄█  ▀▄▄▄▀ █▄▄▄▀ █   █ █▄▄▄▄ █▄▄▄▄ █▄▄▄▀
```

# SUBRECO — Attack Surface Intelligence Platform

A self-hosted **subdomain discovery and attack-surface management** platform for
**authorized** bug-bounty and security reconnaissance. SUBRECO orchestrates a set of
well-known open-source recon tools behind one pipeline, stores everything in PostgreSQL,
and gives you a real-time console to explore the results.

> **Authorized use only.** Scan domains you own or have explicit written permission to
> test. SUBRECO is detection/inventory tooling — it discovers and fingerprints assets.
> It does **not** exploit anything.

---

## What it does

A single scan runs a staged pipeline against one root domain:

1. **Passive enumeration** — crt.sh, AlienVault OTX, RapidDNS, BufferOver, SecurityTrails
   (these need **no external binaries** — just HTTP).
2. **Active enumeration** — subfinder, assetfinder, amass, chaos (used when installed).
3. **Resolution** — dnsx, with a built-in pure-Python `dnspython` fallback.
4. **Liveness & fingerprinting** — httpx (status, title, server, tech, CDN, ASN).
5. **Port scan** — naabu (optional).
6. **Screenshots** — gowitness / headless Chromium (optional).
7. **Wayback & crawl** — waybackurls, gau, katana; URLs categorized (admin/login/api/backup).
8. **JS intelligence** — secret scanning (AWS, GCP, Slack, GitHub, Stripe, JWT, private keys).
9. **Takeover detection** — CNAME fingerprints for S3, GitHub Pages, Heroku, Shopify, Azure,
   Zendesk, Fastly, CloudFront (detection only, with confidence + risk).

**Every tool-based stage degrades gracefully.** If a binary isn't installed, that stage is
skipped with a logged note and the scan continues. This means SUBRECO is genuinely useful
even on a minimal install where only the passive HTTP sources run.

---

## Architecture

```
┌──────────────┐   HTTP/WS   ┌──────────────┐   tasks   ┌──────────────┐
│  Next.js UI  │ ──────────▶ │  FastAPI API │ ────────▶ │ Celery worker│
│ (recon       │ ◀────────── │  + WebSocket │ ◀──────── │ (orchestrator)│
│  console)    │   events    └──────┬───────┘  Redis    └──────┬───────┘
└──────────────┘                    │  pub/sub                 │
                                    ▼                          ▼
                              ┌──────────┐              recon toolchain
                              │ Postgres │              (subfinder, httpx,
                              └──────────┘               naabu, katana, …)
```

- **Backend** — FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT auth + RBAC, audit log.
- **Worker** — Celery on Redis; drives the orchestrator and streams progress over Redis pub/sub.
- **Realtime** — WebSocket fan-out (`/ws/scans/{id}`) so the UI shows live stage progress.
- **Frontend** — Next.js 14 (App Router), Tailwind, Recharts, TanStack Table.
- **Deploy** — Docker Compose with Nginx reverse proxy.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the data model and how to extend a stage.

---

## Quick start (Docker)

```bash
git clone <your-repo> subreco && cd subreco
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY to a long random string.

# Build with the full recon toolchain baked in (slower first build):
INSTALL_TOOLS=true docker compose build
docker compose up -d
```

Then open **http://localhost** and create the operator account (the first registered
user becomes ADMIN). Launch a scan from the dashboard and watch it run live.

To build **without** the Go toolchain (passive sources only, much faster):

```bash
docker compose build        # INSTALL_TOOLS defaults to false
docker compose up -d
```

## Quick start (local dev, no Docker)

```bash
# --- backend ---
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' ../.env | xargs)   # or set vars manually
uvicorn app.main:app --reload             # API on :8000

# in another shell (same venv):
celery -A app.celery_app worker -l info   # needs Redis running

# --- frontend ---
cd ../frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api \
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws \
npm run dev                               # UI on :3000
```

You need **PostgreSQL** and **Redis** reachable (see `.env`). For a fast dev DB:
`docker compose up -d postgres redis`.

---

## Configuration

All configuration is environment-driven (`.env`). Highlights:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key — **set this**. |
| `POSTGRES_*`, `DATABASE_URL` | Database connection. |
| `REDIS_URL` | Celery broker + WebSocket pub/sub. |
| `CORS_ORIGINS` | Allowed frontend origins. |
| `SECURITYTRAILS_API_KEY`, `CHAOS_API_KEY`, `OTX_API_KEY` | Optional — unlock extra passive sources. |
| `DISCORD_WEBHOOK_URL`, `SLACK_WEBHOOK_URL`, `TELEGRAM_*`, `SMTP_*` | Optional scan notifications. |
| `INSTALL_TOOLS` | `true` to bake the Go recon toolchain into the backend image. |

Notification channels activate automatically when their credentials are present and are
skipped silently otherwise.

---

## Tools orchestrated

`subfinder` · `assetfinder` · `amass` · `chaos` · `crt.sh` · `SecurityTrails` · `OTX` ·
`BufferOver` · `RapidDNS` · `dnsx` · `httpx` · `naabu` · `katana` · `gowitness` ·
`waybackurls` · `gau` — plus built-in Python equivalents for DNS resolution, URL
categorization (gf-style), and secret scanning (trufflehog-style).

All are public, open-source projects; SUBRECO is the orchestration and storage layer
on top of them.

---

## Honest scope

This repository is a **complete, runnable foundation** — not a mock. The backend pipeline,
data model, auth, real-time progress, exports, and a multi-page console all work today.
A few areas are deliberately left as clearly-marked extension points rather than padded
with non-functional code:

- **Certificate intelligence** — the model and crt.sh fetch exist; wiring cert population
  into the orchestrator is a documented extension point.
- **Some optional stages** (ports, screenshots) require their binaries; without them the
  stage is skipped, not faked.

`docs/ARCHITECTURE.md` explains exactly where to plug in. Everything advertised as working
has been compile- and build-verified (`py_compile` on all backend modules; `next build`
on the full frontend).

---

## License & responsibility

Provided for lawful, authorized security testing. You are responsible for ensuring you
have permission to scan any target. The authors assume no liability for misuse.
