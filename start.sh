#!/bin/bash

echo "Starting RoroJonggrang Data Scrape..."

# Start Redis
echo "[1/3] Starting Redis..."
docker start redis 2>/dev/null || echo "Redis already running"

# Start Flask
echo "[2/3] Starting Flask server on port 5001..."
PYTHONPATH=$(pwd) python app.py &
FLASK_PID=$!

# Wait for Flask
sleep 3

# Start Celery
echo "[3/3] Starting Celery worker..."
PYTHONPATH=$(pwd) celery -A celery_worker.celery worker --loglevel=info &
CELERY_PID=$!

echo ""
echo "============================================"
echo "  RoroJonggrang Data Scrape is running!    "
echo "============================================"
echo ""
echo "  Web App:  http://localhost:5001"
echo "  Redis:    localhost:6379"
echo "  Celery:   Worker running"
echo ""
echo "  Press Ctrl+C to stop all services"
echo ""

# Trap to stop all on Ctrl+C
trap "echo 'Stopping...'; kill $FLASK_PID $CELERY_PID 2>/dev/null; exit" INT TERM

wait
