#!/usr/bin/env bash
# One-command local bring-up for RealtyRecall.
#
# Creates .env on first run, builds and starts the whole stack (Postgres, Neo4j,
# a bundled LiveKit server, backend, agent, frontend), waits for the backend to
# report healthy, seeds demo data, and prints where to go.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example."
  echo "For voice, add OPENAI_API_KEY and DEEPGRAM_API_KEY to .env, then run this again."
fi

echo "Building and starting the stack (this can take a few minutes the first time)..."
docker compose up -d --build

echo "Waiting for the backend to become healthy..."
status=""
for _ in $(seq 1 60); do
  cid="$(docker compose ps -q backend 2>/dev/null || true)"
  if [ -n "$cid" ]; then
    status="$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "")"
    [ "$status" = "healthy" ] && break
  fi
  sleep 3
done

if [ "$status" != "healthy" ]; then
  echo "Backend did not become healthy in time. Inspect logs with: docker compose logs backend"
  exit 1
fi

echo "Seeding demo data..."
docker compose run --rm seed

cat <<'EOF'

RealtyRecall is up:
  Frontend       http://localhost:5173
  Seeded demo    http://localhost:5173/call/demo   (the seeded buyer line)
  API docs       http://localhost:8000/docs
  Neo4j browser  http://localhost:7474   (neo4j / neo4jpassword)

Voice needs OPENAI_API_KEY and DEEPGRAM_API_KEY in .env. After adding them, run `make up` again.
Talk to the agent right in your terminal (no LiveKit needed):
  docker compose run --rm agent uv run python main.py console

Stop everything with: make down
EOF
