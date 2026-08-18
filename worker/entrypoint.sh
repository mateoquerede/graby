#!/bin/sh
set -eu

export DISPLAY="${DISPLAY:-:99}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
SCREEN_SIZE="${SCREEN_SIZE:-1368x768x24}"

# Ponytail: one shared display for all jobs. Upgrade path: one worker container/display per session.
Xvfb "$DISPLAY" -screen 0 "$SCREEN_SIZE" -ac +extension RANDR &

openbox >/tmp/openbox.log 2>&1 &

x11vnc \
  -display "$DISPLAY" \
  -forever \
  -shared \
  -rfbport "$VNC_PORT" \
  -nopw \
  -noxdamage \
  -xkb \
  >/tmp/x11vnc.log 2>&1 &

websockify --web=/usr/share/novnc/ "$NOVNC_PORT" "localhost:$VNC_PORT" >/tmp/novnc.log 2>&1 &

if [ "${WORKER_HOT_RELOAD:-false}" = "true" ]; then
  exec python -m watchfiles "python /app/worker/worker.py" /app/worker /app/shopping_copilot
fi

exec python /app/worker/worker.py
