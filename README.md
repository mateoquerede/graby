# Graby

**Graby** is an AI shopping assistant that understands natural language and fills your supermarket cart for you.

Visit [heygraby.com](https://heygraby.com).

---

## What it does

1. You describe what you need: *"leche, huevos y pan"*.
2. Graby searches for each product and picks the best match.
3. Your cart gets filled automatically.
4. You review the cart and complete checkout yourself — **Graby never touches your payment**.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14, Tailwind CSS |
| Backend / API | FastAPI (Python) |
| Persistence / queue | PostgreSQL (`FOR UPDATE SKIP LOCKED`) |
| Worker | Python, httpx, Coto HTTP APIs, OpenRouter |

---

## Local development

### Prerequisites

- Docker & Docker Compose
- An [OpenRouter](https://openrouter.ai) API key
- Network access to Coto Digital (the worker discovers the search key automatically)

### Start everything

```bash
cp .env.example .env
# Set OPENROUTER_API_KEY in .env before starting
docker compose up --build
```

This compose setup runs locally with:
- Frontend: Next.js dev server with live refresh
- Backend: Uvicorn `--reload`
- Worker: a separate PostgreSQL-polling process

- Frontend → http://localhost:3000
- API → http://localhost:8000
- API docs → http://localhost:8000/docs

### Run without Docker

**Backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Worker** (from repo root)

```bash
cd worker
pip install -r requirements.txt
python worker.py
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

---

## Security

- Credentials are accepted only by the backend and are never returned to the frontend,
  sent to OpenRouter, or written to logs. They are kept in the pending job payload
  only so the worker can process it; secure the PostgreSQL instance in production.
- Each job uses an isolated in-memory HTTP session that is closed after completion.
- OpenRouter receives only the product descriptions — never credentials.
- Configure `OPENROUTER_MODEL` with a free model first. Add paid model IDs to
  `OPENROUTER_FALLBACK_MODELS` (comma-separated) to use them when the primary
  model is unavailable or rate-limited.

---

## Project structure

```
graby/
├── frontend/          # Next.js chat UI
├── backend/           # FastAPI — job creation, SSE streaming
├── worker/            # HTTP worker + Coto API adapters
│   └── coto/
├── shopping_copilot/  # Search, planner, evaluator, cart helpers
├── database.py          # Shared PostgreSQL job store
├── Procfile             # Heroku web + worker process types
├── docker-compose.yml
└── .env.example
```
