#!/usr/bin/env bash
# Runs once when the devcontainer is created (as the "vscode" user).
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Menyiapkan virtualenv Python (.venv) ..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r tools/requirements.txt

echo "==> Memasang dependensi Node ..."
npm install

if [[ -f content/generated/manifest.json ]]; then
  echo "==> Konten resmi sudah tersedia, melewati build Sphinx."
else
  echo "==> Konten belum ada. Membangun dari dokumentasi resmi CPython ..."
  echo "    (unduh ±22 MB + build Sphinx, butuh beberapa menit)"
  npm run content:build
fi

echo
echo "Selesai. Jalankan:"
echo "  npm run dev"
echo "lalu buka http://localhost:3000"
