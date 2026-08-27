package carrefour

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// TestLoginValidatesPassword verifies the VTEX ID classic flow: startlogin to
// seed the session, then POST classic/validate with a multipart body.
func TestLoginValidatesPassword(t *testing.T) {
	var validateBody string
	var validateCT string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/api/vtexid/pub/authentication/startlogin"):
			if r.Method != http.MethodPost {
				t.Errorf("startlogin method = %s, want POST", r.Method)
			}
			if r.Header.Get("vtex-id-ui-version") == "" {
				t.Error("missing vtex-id-ui-version header")
			}
			w.WriteHeader(http.StatusOK)
			return
		case strings.HasSuffix(r.URL.Path, "/api/vtexid/pub/authentication/classic/validate"):
			if r.Method != http.MethodPost {
				t.Errorf("validate method = %s, want POST", r.Method)
			}
			validateCT = r.Header.Get("Content-Type")
			body, _ := io.ReadAll(r.Body)
			validateBody = string(body)
			json.NewEncoder(w).Encode(map[string]any{
				"authStatus":        "Success",
				"authCookie":        map[string]any{"Name": "VtexIdclientAutCookie_carrefourar", "Value": "tok"},
				"accountAuthCookie": map[string]any{"Name": "VtexIdclientAutCookie_acct", "Value": "tok2"},
			})
			return
		default:
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
	}))
	defer server.Close()

	client := New()
	client.base = server.URL
	if err := client.Login(context.Background(), "user@example.com", "secret"); err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(validateCT, "multipart/form-data") {
		t.Errorf("validate Content-Type = %q, want multipart/form-data", validateCT)
	}
	if !strings.Contains(validateBody, "user@example.com") || !strings.Contains(validateBody, "secret") {
		t.Errorf("validate body = %q, want login+password", validateBody)
	}
}

// TestLoginRejectsInvalidCredentials verifies a validate response without an
// auth cookie is treated as invalid credentials.
func TestLoginRejectsInvalidCredentials(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/api/vtexid/pub/authentication/startlogin"):
			w.WriteHeader(http.StatusOK)
			return
		case strings.HasSuffix(r.URL.Path, "/api/vtexid/pub/authentication/classic/validate"):
			json.NewEncoder(w).Encode(map[string]any{"authStatus": "WrongCredentials", "authCookie": nil, "accountAuthCookie": nil})
			return
		default:
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
	}))
	defer server.Close()

	client := New()
	client.base = server.URL
	err := client.Login(context.Background(), "user@example.com", "wrong")
	if err == nil || !strings.Contains(strings.ToLower(err.Error()), "credenciales") {
		t.Fatalf("expected invalid-credentials error, got: %v", err)
	}
}

// TestBootstrapStoresOrderFormID verifies Bootstrap parses the orderFormId and
// keeps it for later cart mutations.
func TestBootstrapStoresOrderFormID(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !strings.HasSuffix(r.URL.Path, "/api/checkout/pub/orderForm") {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		json.NewEncoder(w).Encode(map[string]any{"orderFormId": "of-123", "items": []any{}})
	}))
	defer server.Close()

	client := New()
	client.base = server.URL
	if err := client.Bootstrap(context.Background()); err != nil {
		t.Fatal(err)
	}
	if client.orderFormID != "of-123" {
		t.Fatalf("orderFormID = %q, want of-123", client.orderFormID)
	}
}

// TestAddItemUsesSKUID verifies AddItem posts the skuId (not productId) to the
// standard VTEX checkout items endpoint and updates the orderForm from the
// response.
func TestAddItemUsesSKUID(t *testing.T) {
	var gotBody map[string]any
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case strings.HasSuffix(r.URL.Path, "/api/checkout/pub/orderForm"):
			json.NewEncoder(w).Encode(map[string]any{"orderFormId": "of-1", "items": []any{}})
			return
		case strings.HasSuffix(r.URL.Path, "/api/checkout/pub/orderForm/of-1/items"):
			if r.Method != http.MethodPost {
				t.Errorf("method = %s, want POST", r.Method)
			}
			json.NewDecoder(r.Body).Decode(&gotBody)
			json.NewEncoder(w).Encode(map[string]any{"orderFormId": "of-2", "items": []any{}})
			return
		default:
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
	}))
	defer server.Close()

	client := New()
	client.base = server.URL
	if err := client.AddItem(context.Background(), "prod1", "sku9", 2); err != nil {
		t.Fatal(err)
	}
	if client.orderFormID != "of-2" {
		t.Fatalf("orderFormID = %q, want of-2", client.orderFormID)
	}
	orderItems, _ := gotBody["orderItems"].([]any)
	item, _ := orderItems[0].(map[string]any)
	if item["id"] != "sku9" {
		t.Errorf("item id = %v, want sku9 (skuId, not productId)", item["id"])
	}
	if item["quantity"] != float64(2) {
		t.Errorf("quantity = %v, want 2", item["quantity"])
	}
	if _, ok := gotBody["persistedQuery"]; ok {
		t.Errorf("body should not contain persistedQuery, got %#v", gotBody)
	}
}

// TestCartURLPlacesOrderFormIDBeforeHash verifies the orderFormId is a query
// parameter BEFORE the #/cart fragment. VTEX checkout reads it from the query
// string; if it's inside the hash the SPA ignores it and loads an empty cart.
func TestCartURLPlacesOrderFormIDBeforeHash(t *testing.T) {
	client := New()
	client.orderFormID = "of-123"
	got := client.CartURL()
	if !strings.Contains(got, "?orderFormId=of-123#/cart") {
		t.Fatalf("CartURL() = %q, want orderFormId before #/cart", got)
	}
	if strings.Contains(got, "#/cart?orderFormId") {
		t.Fatalf("CartURL() = %q, orderFormId must not be inside the hash fragment", got)
	}
}

// TestSearchNormalizesCatalog verifies Search maps the REST catalog array into
// the worker's expected response.results[].data shape, and only surfaces items
// that are actually in stock.
func TestSearchNormalizesCatalog(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !strings.Contains(r.URL.Path, "/api/catalog_system/pub/products/search/") {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		json.NewEncoder(w).Encode([]any{
			map[string]any{
				"productId":   "111",
				"productName": "Coca Cola 1.5 L",
				"items": []any{map[string]any{
					"itemId": "222",
					"sellers": []any{map[string]any{
						"commertialOffer": map[string]any{"Price": 1158.0, "IsAvailable": true},
					}},
				}},
			},
			map[string]any{
				"productId":   "333",
				"productName": "Coca Cola sin stock",
				"items": []any{map[string]any{
					"itemId": "444",
					"sellers": []any{map[string]any{
						"commertialOffer": map[string]any{"Price": 500.0, "IsAvailable": false},
					}},
				}},
			},
		})
	}))
	defer server.Close()

	client := New()
	client.base = server.URL
	payload, err := client.Search(context.Background(), "coca cola")
	if err != nil {
		t.Fatal(err)
	}
	response, _ := payload["response"].(map[string]any)
	results, _ := response["results"].([]any)
	if len(results) != 1 {
		t.Fatalf("results = %d, want 1 (out-of-stock filtered)", len(results))
	}
	data, _ := results[0].(map[string]any)["data"].(map[string]any)
	if data["id"] != "111" || data["sku_id"] != "222" || data["product_list_price"] != 1158.0 {
		t.Fatalf("unexpected normalized data: %#v", data)
	}
}

func TestParsePrice(t *testing.T) {
	cases := []struct {
		value any
		want  float64
		ok    bool
	}{
		{"1158.00", 1158, true},
		{1158.0, 1158, true},
		{"$1.150,00", 1150, true},
		{"1.150,00", 1150, true},
		{"", 0, false},
		{nil, 0, false},
	}
	for _, tc := range cases {
		got, ok := parsePrice(tc.value)
		if ok != tc.ok || (ok && got != tc.want) {
			t.Errorf("parsePrice(%v) = %v, %v; want %v, %v", tc.value, got, ok, tc.want, tc.ok)
		}
	}
}
