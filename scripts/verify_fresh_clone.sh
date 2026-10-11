#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VERIFY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/leaklock-verify.XXXXXX")"

cleanup() {
  rm -rf "$VERIFY_DIR"
}
trap cleanup EXIT

cd "$ROOT"

echo "[1/6] Creating isolated virtual environment"
"$PYTHON_BIN" -m venv "$VERIFY_DIR/venv"

echo "[2/6] Installing pinned dependencies"
"$VERIFY_DIR/venv/bin/python" -m pip install --quiet --upgrade pip
"$VERIFY_DIR/venv/bin/python" -m pip install --quiet -r requirements-lock.txt
"$VERIFY_DIR/venv/bin/python" -m pip check

echo "[3/6] Compiling source"
"$VERIFY_DIR/venv/bin/python" -m compileall -q -x '(^|/)(\.venv|venv|\.git)/' .

echo "[4/6] Running tests without PostgreSQL"
DATABASE_URL=postgresql://test:test@127.0.0.1:1/test DB_HOST=127.0.0.1 DB_PORT=1 \
  "$VERIFY_DIR/venv/bin/python" -m pytest -q

echo "[5/6] Running bundled synthetic sample"
DATABASE_URL=postgresql://test:test@127.0.0.1:1/test DB_HOST=127.0.0.1 DB_PORT=1 \
  "$VERIFY_DIR/venv/bin/python" scripts/scan_sample.py

echo "[6/6] Proving production rejects the development secret"
if env -u FLASK_SECRET_KEY LEAKLOCK_ENV=production \
  "$VERIFY_DIR/venv/bin/python" -c "import config" >/dev/null 2>&1; then
  echo "ERROR: production accepted the development secret" >&2
  exit 1
fi

echo "LEAKLOCK_FRESH_CLONE_VERIFIED"

