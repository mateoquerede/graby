package coto

import "testing"

func TestAddressID(t *testing.T) {
	cases := []struct {
		name  string
		value map[string]any
		want  string
	}{
		{"id", map[string]any{"id": "123"}, "123"},
		{"idDomicilio", map[string]any{"idDomicilio": "456"}, "456"},
		{"address_id", map[string]any{"address_id": "789"}, "789"},
		{"codigo", map[string]any{"codigo": "abc"}, "abc"},
		{"empty", map[string]any{"id": ""}, ""},
		{"nil", map[string]any{"id": nil}, ""},
		{"missing", map[string]any{"other": "x"}, ""},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := addressID(tc.value); got != tc.want {
				t.Errorf("addressID(%v) = %q, want %q", tc.value, got, tc.want)
			}
		})
	}
}

func TestIsSelected(t *testing.T) {
	cases := []struct {
		name  string
		value map[string]any
		want  bool
	}{
		{"true", map[string]any{"selected": true}, true},
		{"string true", map[string]any{"selected": "true"}, true},
		{"s", map[string]any{"default": "s"}, true},
		{"y", map[string]any{"predeterminado": "y"}, true},
		{"1", map[string]any{"seleccionado": "1"}, true},
		{"false", map[string]any{"selected": false}, false},
		{"no", map[string]any{"selected": "no"}, false},
		{"missing", map[string]any{"other": "x"}, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := isSelected(tc.value); got != tc.want {
				t.Errorf("isSelected(%v) = %v, want %v", tc.value, got, tc.want)
			}
		})
	}
}

func TestTrimFloat(t *testing.T) {
	cases := []struct {
		value float64
		want  string
	}{
		{1, "1"},
		{1.5, "1.5"},
		{2.25, "2.25"},
		{0, "0"},
		{3.0, "3"},
	}
	for _, tc := range cases {
		if got := trimFloat(tc.value); got != tc.want {
			t.Errorf("trimFloat(%v) = %q, want %q", tc.value, got, tc.want)
		}
	}
}