#!/bin/sh
# Mirror of .github/workflows/ci.yml run locally in containers (no host Python/Node needed).
# Usage: sh backend/scripts/ci_local.sh [backend|frontend|all|lint]   (default: all)
# backend/frontend/all = the CI jobs; lint = ruff, black, mypy (core/), eslint, prettier only.
set -eu

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
case "$(uname -s)" in MINGW*|MSYS*) ROOT=$(cd "$ROOT" && pwd -W); export MSYS_NO_PATHCONV=1;; esac
NET=specid_ci
DB=specid-ci-db
WHAT=${1:-all}

backend() {
  docker network inspect "$NET" >/dev/null 2>&1 || docker network create "$NET" >/dev/null
  docker rm -f "$DB" >/dev/null 2>&1 || true
  docker run -d --name "$DB" --network "$NET" \
    -e POSTGRES_USER=specid -e POSTGRES_PASSWORD=specid -e POSTGRES_DB=specid postgres:16-alpine >/dev/null
  trap 'docker rm -f "$DB" >/dev/null 2>&1 || true' EXIT
  until docker exec "$DB" pg_isready -U specid -d specid >/dev/null 2>&1; do sleep 1; done
  echo "== backend job (python:3.11-slim, postgres:16-alpine) =="
  docker run --rm --network "$NET" -v "$ROOT/backend":/w -w /w \
    -v specid_pip_cache:/root/.cache/pip \
    -e DATABASE_URL="postgresql+psycopg://specid:specid@$DB:5432/specid" \
    -e DB_HOST="$DB" \
    -e JWT_SECRET=ci-only-secret-0123456789abcdef0123456789 \
    -e EMBEDDINGS_ENABLED=false \
    python:3.11-slim sh -c '
      set -e
      pip install -q --root-user-action=ignore --disable-pip-version-check -r requirements.lock -r requirements-dev.txt
      ruff check .
      black --check .
      pytest -p no:cacheprovider -m "not ml" --cov=app/core --cov-fail-under=70
    '
}

frontend() {
  echo "== frontend job (node:20-alpine) =="
  docker run --rm -v "$ROOT/frontend":/src -w /src \
    -v specid_node_modules:/src/node_modules -v specid_npm_cache:/root/.npm \
    node:20-alpine sh -c '
      set -e
      npm ci --no-audit --no-fund
      npm run lint
      npm test -- --run
      npm run build
    '
}

lint() {
  echo "== lint: ruff, black, mypy core (python:3.11-slim) =="
  docker run --rm -v "$ROOT/backend":/w -w /w -v specid_pip_cache:/root/.cache/pip     python:3.11-slim sh -c '
      set -e
      pip install -q --root-user-action=ignore --disable-pip-version-check -r requirements.lock -r requirements-dev.txt
      ruff check .
      black --check .
      mypy
    '
  echo "== lint: eslint, prettier (node:20-alpine) =="
  docker run --rm -v "$ROOT/frontend":/src -w /src     -v specid_node_modules:/src/node_modules -v specid_npm_cache:/root/.npm     node:20-alpine sh -c 'set -e; npm ci --no-audit --no-fund >/dev/null; npm run lint'
}

case "$WHAT" in
  lint) lint ;;
  backend) backend ;;
  frontend) frontend ;;
  all) backend; frontend ;;
  *) echo "usage: $0 [backend|frontend|all|lint]"; exit 2 ;;
esac
echo "== local CI: $WHAT passed =="
