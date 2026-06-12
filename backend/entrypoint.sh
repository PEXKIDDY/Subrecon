#!/usr/bin/env bash
set -e

# ROLE selects what this container runs: api | worker
ROLE="${ROLE:-api}"

wait_for() {
  echo "Waiting for $1:$2 ..."
  until (echo > "/dev/tcp/$1/$2") 2>/dev/null; do sleep 1; done
  echo "$1:$2 is up."
}

wait_for "${POSTGRES_HOST:-postgres}" "${POSTGRES_PORT:-5432}"
wait_for "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}"

if [ "$ROLE" = "api" ]; then
  echo "Running database migrations..."
  alembic upgrade head || python -c "from app.database import init_db; init_db()"
  echo "Starting API (gunicorn/uvicorn)..."
  exec gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    -w "${WEB_CONCURRENCY:-2}" \
    -b 0.0.0.0:8000 \
    --timeout 120
elif [ "$ROLE" = "worker" ]; then
  echo "Starting Celery worker..."
  exec celery -A app.celery_app.celery_app worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-4}"
else
  echo "Unknown ROLE: $ROLE"; exit 1
fi
