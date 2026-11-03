#!/usr/bin/env bash
set -euo pipefail

python -m app.init_db

exec python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}"