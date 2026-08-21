FROM python:3.12-bullseye

WORKDIR /app

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code and shopping automation helpers (context = repo root)
COPY worker/ /app/worker/
COPY shopping_copilot/ /app/shopping_copilot/

CMD ["python", "/app/worker/worker.py"]
