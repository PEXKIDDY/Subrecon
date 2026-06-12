# Production Deployment Guide

This guide covers running SUBRECO in a production-like environment with Docker Compose
behind Nginx. Adapt freely for Kubernetes or a managed platform.

---

## 1. Prerequisites

- A Linux host (2+ vCPU, 4 GB+ RAM recommended; recon is I/O and burst-CPU heavy).
- Docker Engine 24+ and the Compose plugin.
- A domain name pointing at the host if you want TLS (recommended).

---

## 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and set, at minimum:

- `SECRET_KEY` — generate one: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `POSTGRES_PASSWORD` — a strong password.
- `CORS_ORIGINS` — your real frontend origin(s), comma-separated, e.g. `https://recon.example.com`.
- `NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL` — public URLs the browser will call,
  e.g. `https://recon.example.com/api` and `wss://recon.example.com/ws`.

Optional but recommended:

- API keys (`SECURITYTRAILS_API_KEY`, `CHAOS_API_KEY`, `OTX_API_KEY`) to widen passive coverage.
- Notification credentials for Discord/Slack/Telegram/Email.

---

## 3. Build

Full toolchain (recommended for real recon):

```bash
INSTALL_TOOLS=true docker compose build
```

This compiles the Go recon toolchain (subfinder, httpx, naabu, katana, dnsx, …) into the
backend image. The first build takes several minutes. Subsequent builds are cached.

Lightweight build (passive HTTP sources only):

```bash
docker compose build
```

---

## 4. Run

```bash
docker compose up -d
docker compose ps          # all services healthy?
docker compose logs -f backend worker
```

Services:

| Service   | Role |
|-----------|------|
| `postgres`| Database (volume `pgdata`). |
| `redis`   | Celery broker + WebSocket pub/sub. |
| `backend` | FastAPI API + WebSocket (`ROLE=api`). Runs migrations on start. |
| `worker`  | Celery worker (`ROLE=worker`) running scans. |
| `frontend`| Next.js standalone server. |
| `nginx`   | Reverse proxy on `:80` — routes `/api`, `/ws`, `/screenshots`, and the UI. |

On first start the backend runs `alembic upgrade head` (falling back to `init_db()` if no
migration is present). Register the first user — they become **ADMIN**.

---

## 5. TLS

Terminate TLS at Nginx or in front of it. Two common options:

- **Nginx + certbot**: add a 443 server block and mount certificates into the `nginx` service.
- **External proxy** (Caddy, Traefik, a cloud load balancer): point it at the `nginx`
  service or directly at `frontend`/`backend`, and set `NEXT_PUBLIC_*` to `https`/`wss`.

When using TLS, make sure WebSocket upgrades are preserved (`Upgrade`/`Connection` headers).
The bundled `nginx/nginx.conf` already does this for `/ws/`.

---

## 6. Scaling the worker

Recon is the bottleneck, not the API. Scale workers horizontally:

```bash
docker compose up -d --scale worker=4
```

Each worker pulls scans from Redis independently. Tune Celery concurrency and the recon
timeouts/concurrency in `.env` (`RECON_*` variables).

---

## 7. Backups

- **Database**: back up the `pgdata` volume or use `pg_dump`:
  ```bash
  docker compose exec postgres pg_dump -U subreco subreco > backup.sql
  ```
- **Screenshots**: back up the `screenshots` volume.

---

## 8. Operations

```bash
# Apply new migrations after a code update
docker compose exec backend alembic upgrade head

# Create a migration after changing models
docker compose exec backend alembic revision --autogenerate -m "describe change"

# Tail a single scan's worker activity
docker compose logs -f worker

# Restart just the API after a config change
docker compose restart backend
```

---

## 9. Hardening checklist

- [ ] `SECRET_KEY` is long and unique; never commit `.env`.
- [ ] `CORS_ORIGINS` is restricted to your real origin(s).
- [ ] Postgres is not exposed publicly (no host port mapping in production).
- [ ] TLS terminated; HTTP redirects to HTTPS.
- [ ] Worker runs as non-root (the image already does for the frontend; review backend).
- [ ] Outbound scanning is permitted by your hosting provider's AUP.
- [ ] You scan only authorized targets.
