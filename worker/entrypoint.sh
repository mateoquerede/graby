#!/bin/sh
set -eu

if [ "${WORKER_HOT_RELOAD:-false}" = "true" ]; then
  exec python -m watchfiles "python /app/worker/worker.py" /app/worker /app/shopping_copilot
fi

exec python /app/worker/worker.py
