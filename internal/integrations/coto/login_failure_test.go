package coto

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// TestLoginDetectsInvalidCredentials verifies that the Go worker returns an
// error (and therefore publishes the "No pude iniciar sesión..." FAILED event)
// for every login response shape that the legacy Python worker rejected.
func TestLoginDetectsInvalidCredentials(t *testing.T) {
	cases := []struct {
		name        string
		loginBody   string
		statusCode  int
		wantErr     bool
	}{
		{"success codigoError 0", `{"codigoError":"0","success":true}`, 200, false},
		{"success no codigoError", `{"success":true}`, 200, false},
		{"success empty body", ``, 200, false},
		{"failure success false", `{"success":false,"mensaje":"credenciales inválidas"}`, 200, true},
		{"failure null codigoError", `{"codigoError":null,"mensaje":"credenciales inválidas"}`, 200, true},
		{"failure codigoError non zero string", `{"codigoError":"-1","success":false}`, 200, true},
		{"failure codigoError non zero number", `{"codigoError":1,"success":false}`, 200, true},
		{"failure error field", `{"error":"invalid login"}`, 200, true},
		{"failure http 401", `unauthorized`, 401, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				switch {
				case strings.HasSuffix(r.URL.Path, "/cProfileActor/init"):
					json.NewEncoder(w).Encode(map[string]any{"ok": true})
					return
				case strings.HasSuffix(r.URL.Path, "/getSessionConfirmationNumber"):
					json.NewEncoder(w).Encode(map[string]any{"sessionConfirmationNumber": "sess123"})
					return
				default:
					w.WriteHeader(tc.statusCode)
					w.Write([]byte(tc.loginBody))
					return
				}
			}))
			defer server.Close()

			client := New("search-key")
			client.base = server.URL

			err := client.Login(context.Background(), "user@example.com", "wrong")
			if got := err != nil; got != tc.wantErr {
				t.Errorf("Login() error = %v, wantErr %v", err, tc.wantErr)
			}
			if tc.wantErr && strings.Contains(strings.ToLower(err.Error()), "credenciales") == false {
				t.Errorf("expected invalid-credentials error, got: %v", err)
			}
		})
	}
}