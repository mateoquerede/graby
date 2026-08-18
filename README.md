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
| Queue | Redis |
| Worker | Python, Playwright, Ollama, Xvfb, noVNC |

---

## Local development

### Prerequisites

- Docker & Docker Compose
- [Ollama](https://ollama.com) running locally with `llama3` pulled

```bash
ollama pull llama3
```

### Start everything

```bash
cp .env.example .env
docker compose up --build
```

This compose setup runs in development mode with hot reload:
- Frontend: Next.js dev server with live refresh
- Backend: Uvicorn `--reload`
- Worker: auto-restart on Python changes in `worker/` and `shopping_copilot/`

- Frontend → http://localhost:3000
- API → http://localhost:8000
- API docs → http://localhost:8000/docs
- Live browser (noVNC) → http://localhost:6080/vnc.html

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

- Credentials are **never** stored in any database, log, or analytics tool.
- Each automation job runs in an isolated browser context that is destroyed after completion.
- Ollama receives only the product descriptions — never credentials.
- Redis stores only job status and events, not credentials.

---

## Project structure

```
graby/
├── frontend/          # Next.js chat UI
├── backend/           # FastAPI — job creation, SSE streaming
├── worker/            # Playwright worker + Coto adapters
│   └── coto/
├── shopping_copilot/  # Search, planner, evaluator, cart helpers
├── docker-compose.yml
└── .env.example
```
