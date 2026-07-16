#!/bin/bash

set -e

echo "Starting Roro Jonggrang Data Scrape..."

# Activate virtual environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
  source "$SCRIPT_DIR/venv/bin/activate"
  echo "Virtual environment activated"
fi

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

REDIS_HOST=${REDIS_HOST:-127.0.0.1}
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_READY=false
if command -v nc >/dev/null 2>&1; then
  if nc -z "$REDIS_HOST" "$REDIS_PORT" >/dev/null 2>&1; then
    REDIS_READY=true
  fi
fi

echo "[1/3] Redis: $REDIS_HOST:$REDIS_PORT"
if [ "$REDIS_READY" = true ]; then
  echo "Redis is reachable"
else
  echo "Redis is NOT reachable. Celery/SSE will not work until Redis is started."
fi

# Start Flask
echo "[2/3] Starting Flask server on port 5001..."
PYTHONPATH=$(pwd) python app.py &
FLASK_PID=$!

# Wait for Flask
sleep 3

CELERY_PID=""
if [ "$REDIS_READY" = true ]; then
  echo "[3/3] Starting Celery worker..."
  PYTHONPATH=$(pwd) celery -A celery_worker.celery worker --loglevel=info &
  CELERY_PID=$!
else
  echo "[3/3] Skipping Celery worker because Redis is offline"
fi

echo ""
echo "============================================"
echo "  Roro Jonggrang Data Scrape is running!    "
echo "============================================"
echo ""
echo "  Web App:  http://localhost:5001"
echo "  Redis:    $REDIS_HOST:$REDIS_PORT"
if [ -n "$CELERY_PID" ]; then
  echo "  Celery:   Worker running"
else
  echo "  Celery:   Not started"
fi
echo ""
echo "  Press Ctrl+C to stop all services"
echo ""

if [ -n "$CELERY_PID" ]; then
  trap "echo 'Stopping...'; kill $FLASK_PID $CELERY_PID 2>/dev/null; exit" INT TERM
else
  trap "echo 'Stopping...'; kill $FLASK_PID 2>/dev/null; exit" INT TERM
fi

wait
