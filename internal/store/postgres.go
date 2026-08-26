package store

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"graby/internal/models"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

const jobsSchema = `
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
);`

type Repository struct{ pool *pgxpool.Pool }

func New(ctx context.Context, databaseURL string) (*Repository, error) {
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		return nil, fmt.Errorf("connect PostgreSQL: %w", err)
	}
	return &Repository{pool: pool}, nil
}

func (r *Repository) Close() { r.pool.Close() }
func (r *Repository) Init(ctx context.Context) error {
	if _, err := r.pool.Exec(ctx, jobsSchema); err != nil {
		return err
	}
	_, err := r.pool.Exec(ctx, `CREATE INDEX IF NOT EXISTS jobs_pending_idx ON jobs (status, created_at)`)
	return err
}

func (r *Repository) Create(ctx context.Context, id string, payload models.JobPayload) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	_, err = r.pool.Exec(ctx, `INSERT INTO jobs (id, payload) VALUES ($1, $2)`, id, data)
	return err
}

func (r *Repository) Get(ctx context.Context, id string) (*models.Job, error) {
	row := r.pool.QueryRow(ctx, `SELECT id::text, payload, status, progress, result, last_event, created_at, updated_at FROM jobs WHERE id=$1`, id)
	return scanJob(row)
}

func (r *Repository) Claim(ctx context.Context) (*models.Job, error) {
	row := r.pool.QueryRow(ctx, `UPDATE jobs SET status='STARTING', locked_at=NOW(), updated_at=NOW()
		WHERE id=(SELECT id FROM jobs WHERE status='PENDING' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1)
		RETURNING id::text, payload, status, progress, result, last_event, created_at, updated_at`)
	job, err := scanJob(row)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	return job, err
}

func (r *Repository) Resume(ctx context.Context, id string, confirmed []models.Task, correction string) (bool, error) {
	tx, err := r.pool.Begin(ctx)
	if err != nil {
		return false, err
	}
	defer tx.Rollback(ctx)
	var rawPayload, event []byte
	err = tx.QueryRow(ctx, `SELECT payload, last_event FROM jobs WHERE id=$1 AND status='AWAITING_CONFIRMATION' FOR UPDATE`, id).Scan(&rawPayload, &event)
	if errors.Is(err, pgx.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	var payload models.JobPayload
	if err = json.Unmarshal(rawPayload, &payload); err != nil {
		return false, err
	}
	if confirmed != nil {
		payload.ConfirmedTasks, payload.PreviousTasks, payload.CorrectionMode = confirmed, nil, false
	} else {
		var previous struct {
			Items []models.Task `json:"items"`
		}
		_ = json.Unmarshal(event, &previous)
		payload.ConfirmedTasks, payload.PreviousTasks, payload.Message, payload.CorrectionMode = nil, previous.Items, correction, true
	}
	data, err := json.Marshal(payload)
	if err != nil {
		return false, err
	}
	_, err = tx.Exec(ctx, `UPDATE jobs SET payload=$1, status='PENDING', locked_at=NULL, updated_at=NOW() WHERE id=$2`, data, id)
	if err != nil {
		return false, err
	}
	if err := tx.Commit(ctx); err != nil {
		return false, err
	}
	return true, nil
}

func (r *Repository) Publish(ctx context.Context, id, status, message string, extra map[string]any) error {
	event := models.Event{Type: "status", Status: status, Message: message, Extra: extra}.JSON()
	progress, _ := json.Marshal(extra)
	var result []byte
	if models.IsTerminal(status) {
		items := any([]any{})
		if value, ok := extra["items"]; ok {
			items = value
		}
		result, _ = json.Marshal(map[string]any{"items": items, "total": number(extra["total"]), "checkout_url": extra["checkout_url"]})
	}
	_, err := r.pool.Exec(ctx, `UPDATE jobs SET status=$1, progress=$2, last_event=$3,
		result=CASE WHEN $1::varchar IN ('COMPLETED','FAILED') THEN $4 ELSE result END, updated_at=NOW(),
		locked_at=CASE WHEN $1::varchar IN ('COMPLETED','FAILED') THEN NULL ELSE locked_at END WHERE id=$5`,
		status, progress, event, result, id)
	return err
}

func (r *Repository) RecoverStale(ctx context.Context, age time.Duration) error {
	_, err := r.pool.Exec(ctx, `UPDATE jobs SET status='PENDING', locked_at=NULL, updated_at=NOW()
		WHERE status NOT IN ('PENDING','COMPLETED','FAILED','AWAITING_CONFIRMATION')
		AND locked_at < NOW() - $1::interval`, fmt.Sprintf("%f seconds", age.Seconds()))
	return err
}

type rowScanner interface{ Scan(...any) error }

func scanJob(row rowScanner) (*models.Job, error) {
	var job models.Job
	var payload []byte
	err := row.Scan(&job.ID, &payload, &job.Status, &job.Progress, &job.Result, &job.LastEvent, &job.CreatedAt, &job.UpdatedAt)
	if err != nil {
		return nil, err
	}
	if err := json.Unmarshal(payload, &job.Payload); err != nil {
		return nil, err
	}
	return &job, nil
}
func number(value any) any {
	if value == nil {
		return 0
	}
	return value
}
