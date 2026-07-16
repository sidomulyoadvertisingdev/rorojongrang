#!/bin/bash

echo "Stopping Roro Jonggrang Data Scrape..."

# Stop Celery
pkill -f "celery -A celery_worker" 2>/dev/null && echo "Celery stopped" || echo "Celery not running"

# Stop Flask
pkill -f "python app.py" 2>/dev/null && echo "Flask stopped" || echo "Flask not running"

# Stop Redis (optional, comment out if you want Redis to keep running)
# docker stop redis 2>/dev/null && echo "Redis stopped" || echo "Redis not running"

echo "All services stopped!"
