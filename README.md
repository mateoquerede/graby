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
| Backend / API | Go (`net/http`, SSE and WebSocket) |
| Persistence / queue | PostgreSQL (`FOR UPDATE SKIP LOCKED`) |
| Worker | Go, Coto HTTP APIs, OpenRouter |

---

## Local development

### Prerequisites

- Docker & Docker Compose
- An [OpenRouter](https://openrouter.ai) API key
- Network access to Coto Digital (the worker discovers the search key automatically)
- Go 1.22+ when running the API or worker without Docker

### Start everything

```bash
cp .env.example .env
# Set OPENROUTER_API_KEY in .env before starting
docker compose up --build
```

This compose setup runs locally with:
- Frontend: Next.js dev server with live refresh
- API: a Go HTTP service
- Worker: a separate Go PostgreSQL-polling process

- Frontend → http://localhost:3000
- API → http://localhost:8000

### Run without Docker

**API**

```bash
go run ./cmd/api
```

**Worker** (from repo root)

```bash
go run ./cmd/worker
```

Both commands read the repository `.env` file for local development; deployment
environment variables take precedence.

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

---

## Go migration

The active runtime is Go. `cmd/api` exposes the existing purchase HTTP
contract (`POST /api/purchases`, status, confirmation, SSE, WebSocket, and
`GET /health`); `cmd/worker` claims PostgreSQL jobs with `SKIP LOCKED`.

Implementation packages are deliberately separated by responsibility:

- `internal/models`: typed API, job, event, cart, and task models.
- `internal/store`: PostgreSQL schema, queue claiming, event persistence, and
  stale-job recovery.
- `internal/openrouter`: model fallback and JSON-completion adapter.
- `internal/coto`: isolated cookie-based Coto session, authentication, search,
  delivery-address selection, and cart adapter.
- `internal/worker`: planning, candidate ranking, cart processing, and worker
  event publication.

The historical Python directories remain in the tree as migration reference
and are not used by Compose or the root Docker targets.

## Security

- Credentials are accepted only by the backend and are never returned to the frontend,
  sent to OpenRouter, or written to logs. They are kept in the pending job payload
  only so the worker can process it; secure the PostgreSQL instance in production.
- Each job uses an isolated in-memory HTTP session that is closed after completion.
- OpenRouter is called only by the worker through its internal Go adapter; its API key
  comes from `OPENROUTER_API_KEY` and is never exposed to the frontend.
- OpenRouter receives only the product descriptions — never Coto credentials.
- Configure `OPENROUTER_MODEL` with a free model first. Add paid model IDs to
  `OPENROUTER_FALLBACK_MODELS` (comma-separated) to use them when the primary
  model is unavailable or rate-limited.

---

## Project structure

```
graby/
├── frontend/          # Next.js chat UI
├── cmd/api/           # Go HTTP API entry point
├── cmd/worker/        # Go worker entry point
├── internal/          # API, typed models, Postgres, Coto and OpenRouter packages
├── backend/, worker/, shopping_copilot/ # Historical Python migration reference
├── Procfile             # Heroku web + worker process types
├── docker-compose.yml
└── .env.example
```
