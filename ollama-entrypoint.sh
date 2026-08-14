#!/bin/sh
# Start Ollama server in the background, pull the configured model, then wait.

MODEL="${OLLAMA_MODEL:-llama3.2}"

ollama serve &
SERVER_PID=$!

# Wait for the server to be ready
until ollama list >/dev/null 2>&1; do
  sleep 1
done

# Pull model if not already present
if ! ollama list | grep -q "^${MODEL}"; then
  echo "[entrypoint] Pulling model: ${MODEL}"
  ollama pull "${MODEL}"
fi

echo "[entrypoint] Model ${MODEL} ready"
wait "$SERVER_PID"
