package api

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"

	"graby/internal/models"
	"graby/internal/store"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	"github.com/jackc/pgx/v5"
)

type Server struct {
	repo    *store.Repository
	origins map[string]bool
	version string
}

func New(repo *store.Repository, origins []string, version string) *Server {
	allowed := make(map[string]bool, len(origins))
	for _, origin := range origins {
		allowed[origin] = true
	}
	return &Server{repo: repo, origins: allowed, version: version}
}

func (s *Server) Handler() http.Handler {
	return s.cors(http.HandlerFunc(s.route))
}

func (s *Server) route(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/health" && r.Method == http.MethodGet {
		writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
		return
	}
	if r.URL.Path == "/version" && r.Method == http.MethodGet {
		writeJSON(w, http.StatusOK, map[string]string{"version": s.version})
		return
	}
	const prefix = "/api/purchases"
	if r.URL.Path == prefix && r.Method == http.MethodPost {
		s.create(w, r)
		return
	}
	if !strings.HasPrefix(r.URL.Path, prefix+"/") {
		notFound(w)
		return
	}
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, prefix+"/"), "/")
	if len(parts) < 1 || parts[0] == "" {
		notFound(w)
		return
	}
	id := parts[0]
	switch {
	case len(parts) == 1 && r.Method == http.MethodGet:
		s.status(w, r, id)
	case len(parts) == 2 && parts[1] == "confirm" && r.Method == http.MethodPost:
		s.confirm(w, r, id)
	case len(parts) == 2 && parts[1] == "events" && r.Method == http.MethodGet:
		s.events(w, r, id)
	case len(parts) == 2 && parts[1] == "ws" && r.Method == http.MethodGet:
		s.ws(w, r, id)
	default:
		notFound(w)
	}
}

func (s *Server) create(w http.ResponseWriter, r *http.Request) {
	var body models.PurchaseRequest
	if err := decode(r, &body); err != nil {
		badRequest(w, "JSON inválido")
		return
	}
	body.Message, body.Email = strings.TrimSpace(body.Message), strings.TrimSpace(body.Email)
	if body.Message == "" || body.Email == "" || body.Password == "" {
		badRequest(w, "message, email y password son obligatorios")
		return
	}
	id := uuid.NewString()
	if err := s.repo.Create(r.Context(), id, models.JobPayload{Email: body.Email, Password: body.Password, Message: body.Message}); err != nil {
		serverError(w, err)
		return
	}
	writeJSON(w, http.StatusAccepted, map[string]string{"job_id": id, "status": models.StatusPending})
}

func (s *Server) status(w http.ResponseWriter, r *http.Request, id string) {
	job, err := s.repo.Get(r.Context(), id)
	if errors.Is(err, pgx.ErrNoRows) {
		notFound(w)
		return
	}
	if err != nil {
		serverError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"job_id": job.ID, "status": job.Status, "progress": rawOrObject(job.Progress),
		"result": rawOrNil(job.Result), "last_event": json.RawMessage(job.Event()),
	})
}

func (s *Server) confirm(w http.ResponseWriter, r *http.Request, id string) {
	var body models.ConfirmationRequest
	if err := decode(r, &body); err != nil {
		badRequest(w, "JSON inválido")
		return
	}
	var confirmed []models.Task
	if body.Confirmed {
		if len(body.Items) == 0 {
			badRequest(w, "items are required when confirming")
			return
		}
		for _, item := range body.Items {
			item.Query = strings.TrimSpace(item.Query)
			if item.Query == "" || item.Quantity < 1 {
				badRequest(w, "items inválidos")
				return
			}
		}
		confirmed = body.Items
	} else if strings.TrimSpace(body.Message) == "" {
		badRequest(w, "message is required when correcting")
		return
	}
	resumed, err := s.repo.Resume(r.Context(), id, confirmed, strings.TrimSpace(body.Message))
	if err != nil {
		serverError(w, err)
		return
	}
	if resumed {
		writeJSON(w, http.StatusOK, map[string]string{"job_id": id, "status": models.StatusPending})
		return
	}
	job, err := s.repo.Get(r.Context(), id)
	if errors.Is(err, pgx.ErrNoRows) {
		notFound(w)
		return
	}
	if err != nil {
		serverError(w, err)
		return
	}
	switch job.Status {
	case "PENDING", "STARTING", "AUTHENTICATING", "AUTHENTICATED", "SEARCHING_PRODUCTS", "COMPLETED":
		writeJSON(w, http.StatusOK, map[string]string{"job_id": id, "status": job.Status})
	default:
		writeError(w, http.StatusConflict, "El pedido ya no espera confirmación.")
	}
}

func (s *Server) events(w http.ResponseWriter, r *http.Request, id string) {
	if !s.exists(w, r.Context(), id) {
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("X-Accel-Buffering", "no")
	w.Header().Set("Connection", "keep-alive")
	flusher, ok := w.(http.Flusher)
	if !ok {
		serverError(w, fmt.Errorf("response streaming unsupported"))
		return
	}
	s.stream(r.Context(), id, func(event []byte) error {
		_, err := fmt.Fprintf(w, "event: worker_status\ndata: %s\n\n", event)
		flusher.Flush()
		return err
	})
}

func (s *Server) ws(w http.ResponseWriter, r *http.Request, id string) {
	if !s.exists(w, r.Context(), id) {
		return
	}
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool {
		origin := r.Header.Get("Origin")
		return origin == "" || s.origins[origin]
	}}
	connection, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer connection.Close()
	_ = connection.SetReadDeadline(time.Now().Add(2 * time.Hour))
	s.stream(r.Context(), id, func(event []byte) error { return connection.WriteMessage(websocket.TextMessage, event) })
}

func (s *Server) stream(ctx context.Context, id string, send func([]byte) error) {
	var last time.Time
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	for {
		job, err := s.repo.Get(ctx, id)
		if err != nil {
			return
		}
		if !job.UpdatedAt.Equal(last) {
			last = job.UpdatedAt
			if send(job.Event()) != nil {
				return
			}
		}
		if models.IsTerminal(job.Status) {
			return
		}
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
		}
	}
}

func (s *Server) exists(w http.ResponseWriter, ctx context.Context, id string) bool {
	_, err := s.repo.Get(ctx, id)
	if errors.Is(err, pgx.ErrNoRows) {
		notFound(w)
		return false
	}
	if err != nil {
		serverError(w, err)
		return false
	}
	return true
}

func (s *Server) cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		if origin != "" && s.origins[origin] {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Credentials", "true")
			w.Header().Set("Vary", "Origin")
		}
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func decode(r *http.Request, target any) error {
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	return decoder.Decode(target)
}
func rawOrObject(raw json.RawMessage) any {
	if len(raw) == 0 || string(raw) == "null" {
		return map[string]any{}
	}
	return raw
}
func rawOrNil(raw json.RawMessage) any {
	if len(raw) == 0 || string(raw) == "null" {
		return nil
	}
	return raw
}
func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
func writeError(w http.ResponseWriter, status int, detail string) {
	writeJSON(w, status, map[string]string{"detail": detail})
}
func badRequest(w http.ResponseWriter, detail string) { writeError(w, http.StatusBadRequest, detail) }
func notFound(w http.ResponseWriter)                  { writeError(w, http.StatusNotFound, "Job not found") }
func serverError(w http.ResponseWriter, err error) {
	writeError(w, http.StatusInternalServerError, "Internal server error")
}
