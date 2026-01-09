#!/bin/bash
# entrypoint.sh - Docker entrypoint for ILM Red API
#
# This script runs database migrations before starting the application.
# It ensures the database schema is up-to-date on every deployment.

set -e

echo "============================================"
echo "  ILM Red API - Starting Up"
echo "============================================"

# Run database migrations
echo ""
echo "[1/2] Running database migrations..."
alembic upgrade head
echo "      Migrations completed successfully."

# Start the application
echo ""
echo "[2/2] Starting uvicorn server..."
echo "============================================"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
