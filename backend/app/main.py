"""FastAPI entry point for asynchronous purchase jobs."""

import asyncio
import json
import os
import sys
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import create_job, get_job, init_db  # noqa: E402

load_dotenv()

TERMINAL_STATUSES = {"COMPLETED", "FAILED"}
app = FastAPI(title="Graby API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


class PurchaseRequest(BaseModel):
    message: str
    email: str
    password: str

    @field_validator("message", "email")
    @classmethod
    def required_text(cls, value: str):
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value.strip()

    @field_validator("password")
    @classmethod
    def required_password(cls, value: str):
        if not value:
            raise ValueError("password cannot be empty")
        return value


def event_for(job: dict) -> dict:
    event = job.get("last_event")
    if isinstance(event, str):
        event = json.loads(event)
    return event or {"type": "status", "status": job["status"], "message": ""}


def serialize_job(job: dict) -> dict:
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress": job.get("progress") or {},
        "result": job.get("result"),
        "last_event": event_for(job),
    }


@app.post("/api/purchases", status_code=202)
def create_purchase(body: PurchaseRequest):
    job_id = str(uuid.uuid4())
    create_job(job_id, {
        "email": body.email,
        "password": body.password,
        "message": body.message,
    })
    return {"job_id": job_id, "status": "PENDING"}


@app.get("/api/purchases/{job_id}")
def purchase_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return serialize_job(job)


async def stream_events(job_id: str):
    last_updated = None
    while True:
        job = get_job(job_id)
        if not job:
            return
        if job["updated_at"] != last_updated:
            last_updated = job["updated_at"]
            yield f"event: worker_status\ndata: {json.dumps(event_for(job))}\n\n"
        if job["status"] in TERMINAL_STATUSES:
            return
        await asyncio.sleep(1)


@app.get("/api/purchases/{job_id}/events")
async def purchase_events(job_id: str):
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return StreamingResponse(
        stream_events(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.websocket("/api/purchases/{job_id}/ws")
async def purchase_events_ws(websocket: WebSocket, job_id: str):
    if not get_job(job_id):
        await websocket.close(code=4404, reason="Job not found")
        return
    await websocket.accept()
    try:
        last_updated = None
        while True:
            job = get_job(job_id)
            if not job:
                return
            if job["updated_at"] != last_updated:
                last_updated = job["updated_at"]
                await websocket.send_text(json.dumps(event_for(job)))
            if job["status"] in TERMINAL_STATUSES:
                return
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return


@app.get("/health")
def health():
    return {"ok": True}
