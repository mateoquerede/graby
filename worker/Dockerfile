FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    libxt6 libxext6 libfontconfig1 ca-certificates \
    libxcb-shm0 libxcursor1 libgtk-3-0 libpangocairo-1.0-0 \
    libpango-1.0-0 libcairo-gobject2 libcairo2 libgdk-pixbuf-xlib-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    python -m playwright install firefox

# Copy worker code and the shared shopping logic (context = repo root)
COPY worker/ /app/worker/
COPY shopping_copilot/ /app/shopping_copilot/
COPY shared/ /app/shared/

CMD ["python", "worker/worker.py"]
