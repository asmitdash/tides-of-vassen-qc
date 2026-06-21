#!/usr/bin/env bash
set -euo pipefail

echo "Netflix QC Pipeline Bootstrap"
echo "=============================="

cd "$(dirname "$0")/.."

# 1. Install Python dependencies
echo "Installing Python dependencies..."
python -m pip install -r backend/requirements.txt

# 2. Start PocketBase in background
echo "Starting PocketBase..."
./pocketbase.exe serve --http=127.0.0.1:8090 &
PB_PID=$!
echo $PB_PID > /tmp/pb-tov.pid
echo "PocketBase started with PID $PB_PID"

# Wait for PocketBase to be ready
sleep 3
echo "Waiting for PocketBase API..."
for i in {1..10}; do
  if curl -s http://127.0.0.1:8090/api/health > /dev/null 2>&1; then
    echo "PocketBase is ready."
    break
  fi
  sleep 1
done

# 3. Apply migrations
echo "Applying migrations..."
./pocketbase.exe migrate up

# 4. Create superuser
echo "Creating superuser..."
PB_ADMIN_EMAIL="${PB_ADMIN_EMAIL:-admin@local.test}"
PB_ADMIN_PASSWORD="${PB_ADMIN_PASSWORD:-TidesOfVassen!2026}"
./pocketbase.exe superuser upsert "$PB_ADMIN_EMAIL" "$PB_ADMIN_PASSWORD"

# 5. Seed the database
echo "Seeding database..."
python -m ingestion.seed_db

echo ""
echo "Bootstrap complete!"
echo "PocketBase PID: $(cat /tmp/pb-tov.pid)"
echo "To start the backend, run: ./scripts/start_backend.sh"
