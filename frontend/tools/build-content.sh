#!/usr/bin/env bash
# Build the official-docs content bundle.
#
# Uses .venv when available (the devcontainer creates it), otherwise the
# system Python. Any arguments are forwarded to tools/fetch_docs.py.
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x ".venv/bin/python" ]]; then
    PYTHON_BIN=".venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

if ! "$PYTHON_BIN" -c "import sphinx, bs4, lxml" >/dev/null 2>&1; then
  cat <<'EOF'
Dependensi Python belum lengkap.

Jalankan:
  python3 -m venv .venv
  .venv/bin/pip install -r tools/requirements.txt

Lalu ulangi:
  npm run content:build
EOF
  exit 1
fi

exec "$PYTHON_BIN" tools/fetch_docs.py "$@"
