"""
Graby — backend API

Routes:
  POST /api/purchases          — create a new purchase job
  GET  /api/purchases/{job_id} — get job status (polling fallback)
  GET  /api/purchases/{job_id}/events — SSE stream of worker events
"""

import asyncio
import json
import os
import uuid

import redis.asyncio as aioredis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
QUEUE_KEY = "graby:jobs"

app = FastAPI(title="Graby API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_redis_sync():
    return aioredis.from_url(REDIS_URL, decode_responses=True)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class PurchaseRequest(BaseModel):
    message: str
    email: str
    password: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v):
        if not v.strip():
            raise ValueError("message cannot be empty")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_not_empty(cls, v):
        if not v.strip():
            raise ValueError("email cannot be empty")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v):
        if not v.strip():
            raise ValueError("password cannot be empty")
        return v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/purchases", status_code=202)
async def create_purchase(body: PurchaseRequest):
    job_id = str(uuid.uuid4())

    # Credentials travel only in the Redis queue payload and are
    # never stored in any database or log.
    job_payload = json.dumps(
        {
            "job_id": job_id,
            "email": body.email,
            "password": body.password,
            "message": body.message,
        }
    )

    r = get_redis_sync()
    await r.hset(f"graby:job:{job_id}", mapping={"status": "PENDING", "last_message": ""})
    await r.rpush(QUEUE_KEY, job_payload)
    await r.aclose()

    return {"job_id": job_id, "status": "PENDING"}


@app.get("/api/purchases/{job_id}")
async def get_purchase(job_id: str):
    r = get_redis_sync()
    data = await r.hgetall(f"graby:job:{job_id}")
    await r.aclose()

    if not data:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"job_id": job_id, **data}


@app.get("/api/purchases/{job_id}/events")
async def purchase_events(job_id: str):
    """Server-Sent Events stream for a purchase job."""

    async def event_generator():
        r = get_redis_sync()
        pubsub = r.pubsub()
        await pubsub.subscribe(f"graby:events:{job_id}")

        terminal_statuses = {"COMPLETED", "FAILED"}

        try:
            # Send initial ping so the browser connection opens immediately
            yield "event: ping\ndata: {}\n\n"

            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)

                if message and message["type"] == "message":
                    data = message["data"]
                    yield f"event: worker_status\ndata: {data}\n\n"

                    try:
                        parsed = json.loads(data)
                        if parsed.get("status") in terminal_statuses:
                            break
                    except json.JSONDecodeError:
                        pass

                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(f"graby:events:{job_id}")
            await r.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {"ok": True}
