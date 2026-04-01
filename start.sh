#!/bin/bash
# Helix — one command to run everything
set -e

echo "Starting Helix..."

# Check .env exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example"
fi

# Start infrastructure
docker compose up -d postgres 2>/dev/null
sleep 2

# Run migrations
uv run alembic upgrade head 2>/dev/null

# Seed a test org
uv run python3 -c "
import asyncio, logging; logging.disable(50)
import structlog; structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(50))
async def seed():
    from helix.db.engine import get_session_factory
    from sqlalchemy import text
    factory = get_session_factory()
    async with factory() as s:
        await s.execute(text(\"INSERT INTO orgs (id, name, slug) VALUES ('00000000-0000-0000-0000-000000000001', 'Demo Org', 'demo') ON CONFLICT DO NOTHING\"))
        await s.commit()
asyncio.run(seed())
" 2>/dev/null

# Start API in background
uv run uvicorn helix.main:app --port 8000 &
API_PID=$!
sleep 2

# Start frontend in background
cd frontend && npm run dev -- --port 3000 &
FRONT_PID=$!
cd ..

echo ""
echo "============================================"
echo "  Helix is running"
echo "============================================"
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  API:       http://localhost:8000"
echo "  Health:    http://localhost:8000/health"
echo ""
echo "  Click 'Dev Login' on the frontend to enter."
echo "  Press Ctrl+C to stop everything."
echo ""

# Wait and cleanup on exit
trap "kill $API_PID $FRONT_PID 2>/dev/null; echo 'Stopped.'" EXIT
wait
