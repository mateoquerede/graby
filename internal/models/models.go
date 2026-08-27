package models

import (
	"encoding/json"
	"time"
)

const (
	StatusPending              = "PENDING"
	StatusAwaitingConfirmation = "AWAITING_CONFIRMATION"
	StatusCompleted            = "COMPLETED"
	StatusFailed               = "FAILED"
)

func IsTerminal(status string) bool { return status == StatusCompleted || status == StatusFailed }

type PurchaseRequest struct {
	Message  string `json:"message"`
	Email    string `json:"email"`
	Password string `json:"password"`
	Provider string `json:"provider"`
}

type ConfirmationRequest struct {
	Confirmed bool   `json:"confirmed"`
	Message   string `json:"message"`
	Items     []Task `json:"items"`
}

type Task struct {
	Query    string  `json:"query"`
	Quantity float64 `json:"quantity"`
}

type JobPayload struct {
	Email          string `json:"email"`
	Password       string `json:"password"`
	Message        string `json:"message"`
	Provider       string `json:"provider,omitempty"`
	ConfirmedTasks []Task `json:"confirmed_tasks,omitempty"`
	PreviousTasks  []Task `json:"previous_tasks,omitempty"`
	CorrectionMode bool   `json:"correction_mode,omitempty"`
}

type Event struct {
	Type    string         `json:"type"`
	Status  string         `json:"status"`
	Message string         `json:"message"`
	Extra   map[string]any `json:"-"`
}

func (e Event) JSON() []byte {
	value := make(map[string]any, len(e.Extra)+3)
	value["type"], value["status"], value["message"] = e.Type, e.Status, e.Message
	for key, item := range e.Extra {
		value[key] = item
	}
	data, _ := json.Marshal(value)
	return data
}

type Job struct {
	ID        string
	Payload   JobPayload
	Status    string
	Progress  json.RawMessage
	Result    json.RawMessage
	LastEvent json.RawMessage
	CreatedAt time.Time
	UpdatedAt time.Time
}

func (j Job) Event() []byte {
	if len(j.LastEvent) > 0 && string(j.LastEvent) != "null" {
		return j.LastEvent
	}
	return Event{Type: "status", Status: j.Status, Message: ""}.JSON()
}

type Product struct {
	Requested string  `json:"requested,omitempty"`
	Name      string  `json:"name"`
	PLU       string  `json:"plu"`
	Quantity  float64 `json:"quantity"`
	Price     float64 `json:"price"`
	Reason    string  `json:"reason"`
	ProductID string  `json:"-"`
	SKUID     string  `json:"-"`
	UnitPrice float64 `json:"-"`
}
