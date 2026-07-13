#!/bin/bash

set -e

echo "Starting RoroJonggrang locally..."

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Created .env from .env.example. Please review the values first."
  else
    echo "Missing .env and .env.example"
    exit 1
  fi
fi

REDIS_HOST=${REDIS_HOST:-127.0.0.1}
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_READY=false
if command -v nc >/dev/null 2>&1; then
  if nc -z "$REDIS_HOST" "$REDIS_PORT" >/dev/null 2>&1; then
    REDIS_READY=true
  fi
fi

echo "[1/2] Starting Flask server on port 5001..."
PYTHONPATH=$(pwd) python app.py &
FLASK_PID=$!

sleep 3

if ! kill -0 "$FLASK_PID" >/dev/null 2>&1; then
  echo "Flask failed to start. Check the traceback above."
  exit 1
fi

if [ "$REDIS_READY" = true ]; then
  echo "[2/2] Starting Celery worker..."
  PYTHONPATH=$(pwd) celery -A celery_worker.celery worker --loglevel=info &
  CELERY_PID=$!
else
  echo "[2/2] Redis is not reachable on $REDIS_HOST:$REDIS_PORT"
  echo "Celery will be skipped for now. Start Redis first, then rerun this script."
  CELERY_PID=""
fi

echo ""
echo "============================================"
echo "  RoroJonggrang Data Scrape is running!    "
echo "============================================"
echo ""
echo "  Web App:  http://localhost:5001"
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
