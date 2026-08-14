FROM python:3.12-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    fonts-liberation libgdk-pixbuf2.0-0 fonts-unifont fonts-noto-color-emoji \
    xvfb x11vnc novnc websockify openbox \
    && rm -rf /var/lib/apt/lists/*

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

# Copy worker code and shopping automation helpers (context = repo root)
COPY worker/ /app/worker/
COPY shopping_copilot/ /app/shopping_copilot/

RUN sed -i 's/\r$//' /app/worker/entrypoint.sh && chmod +x /app/worker/entrypoint.sh

CMD ["/app/worker/entrypoint.sh"]
