"""Small PostgreSQL job store shared by the API and worker."""

import json
import os
import time
import psycopg
from psycopg.rows import dict_row


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    payload JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    progress JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    last_event JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS jobs_pending_idx ON jobs (status, created_at);
"""


def database_url() -> str:
    return os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/graby")


def connect():
    return psycopg.connect(database_url(), row_factory=dict_row)


def init_db() -> None:
    with connect() as conn:
        conn.execute(SCHEMA)


def create_job(job_id: str, payload: dict) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO jobs (id, payload) VALUES (%s, %s)",
            (job_id, json.dumps(payload)),
        )


def resume_job(job_id: str, *, confirmed_tasks: list[dict] | None = None,
               message: str | None = None) -> bool:
    """Put a paused job back in the queue with confirmation or a correction."""
    with connect() as conn:
        row = conn.execute(
            "SELECT payload, last_event FROM jobs WHERE id = %s AND status = 'AWAITING_CONFIRMATION' FOR UPDATE",
            (job_id,),
        ).fetchone()
        if not row:
            return False

        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        if confirmed_tasks is not None:
            payload["confirmed_tasks"] = confirmed_tasks
        else:
            previous_event = row["last_event"]
            if isinstance(previous_event, str):
                previous_event = json.loads(previous_event)
            payload["previous_tasks"] = (previous_event or {}).get("items", [])
            payload.pop("confirmed_tasks", None)
            payload["message"] = message
            payload["correction_mode"] = True

        conn.execute(
            """UPDATE jobs
               SET payload = %s, status = 'PENDING', locked_at = NULL,
                   updated_at = NOW()
               WHERE id = %s""",
            (json.dumps(payload), job_id),
        )
        return True


def get_job(job_id: str) -> dict | None:
    with connect() as conn:
        return conn.execute(
            """SELECT id::text AS job_id, status, progress, result, last_event,
                      created_at, updated_at
               FROM jobs WHERE id = %s""",
            (job_id,),
        ).fetchone()


def claim_job() -> dict | None:
    """Claim one pending job; SKIP LOCKED makes this safe for many workers."""
    with connect() as conn:
        row = conn.execute(
            """UPDATE jobs
               SET status = 'STARTING', locked_at = NOW(), updated_at = NOW()
               WHERE id = (
                   SELECT id FROM jobs
                   WHERE status = 'PENDING'
                   ORDER BY created_at
                   FOR UPDATE SKIP LOCKED
                   LIMIT 1
               )
               RETURNING id::text AS job_id, payload""",
        ).fetchone()
        if not row:
            return None
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return {"job_id": row["job_id"], **payload}


def publish(job_id: str, status: str, message: str, **extra) -> None:
    event = {"type": "status", "status": status, "message": message, **extra}
    with connect() as conn:
        conn.execute(
            """UPDATE jobs
               SET status = %s, progress = %s, last_event = %s,
                   result = CASE WHEN %s IN ('COMPLETED', 'FAILED') THEN %s ELSE result END,
                   updated_at = NOW(), locked_at = CASE WHEN %s IN ('COMPLETED', 'FAILED') THEN NULL ELSE locked_at END
               WHERE id = %s""",
            (
                status,
                json.dumps(extra),
                json.dumps(event),
                status,
                json.dumps({"items": extra.get("items", []), "total": extra.get("total", 0),
                            "checkout_url": extra.get("checkout_url")}),
                status,
                job_id,
            ),
        )


def recover_stale_jobs(max_age_seconds: int = 900) -> None:
    with connect() as conn:
        conn.execute(
            """UPDATE jobs SET status = 'PENDING', locked_at = NULL, updated_at = NOW()
               WHERE status NOT IN ('PENDING', 'COMPLETED', 'FAILED', 'AWAITING_CONFIRMATION')
                 AND locked_at < NOW() - (%s * INTERVAL '1 second')""",
            (max_age_seconds,),
        )


def wait_for_job(interval: float = 1.0):
    time.sleep(interval)
