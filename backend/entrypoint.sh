#!/bin/bash
set -e

# Run Alembic migrations to ensure the database schema is up-to-date
echo "Running Alembic database migrations..."
alembic upgrade head

# Execute the main container command
echo "Starting application..."
exec "$@"
