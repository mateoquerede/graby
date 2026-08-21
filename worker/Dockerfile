FROM python:3.12-bullseye

WORKDIR /app

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker/ /app/worker/
COPY shopping_copilot/ /app/shopping_copilot/
COPY database.py /app/database.py

CMD ["python", "/app/worker/main.py"]
