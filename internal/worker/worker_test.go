package worker

import (
	"testing"

	"github.com/heygraby/graby/internal/models"
)

func TestParsePromptPreservesQuantitiesAndSingularizes(t *testing.T) {
	items := parsePrompt("2 huevos, harina y 1.5 litros de leche")
	if len(items) != 3 {
		t.Fatalf("got %d items, want 3", len(items))
	}
	want := []models.Task{{Query: "huevo", Quantity: 2}, {Query: "harina", Quantity: 1}, {Query: "leche", Quantity: 1.5}}
	for index := range want {
		if items[index] != want[index] {
			t.Errorf("item %d = %#v, want %#v", index, items[index], want[index])
		}
	}
}

func TestChooseProductPrefersSemanticMatch(t *testing.T) {
	payload := map[string]any{"response": map[string]any{"results": []any{
		map[string]any{"data": map[string]any{"id": "prod0001", "sku_id": "one", "sku_plu": "1", "sku_display_name": "Leche entera 1 L", "product_list_price": "2000"}},
		map[string]any{"data": map[string]any{"id": "prod0002", "sku_id": "two", "sku_plu": "2", "sku_display_name": "Yogur frutilla", "product_list_price": "100"}},
	}}}
	product, err := chooseProduct(models.Task{Query: "leche entera", Quantity: 2}, payload)
	if err != nil {
		t.Fatal(err)
	}
	if product.PLU != "1" || product.Quantity != 2 || product.Price != 2000 {
		t.Fatalf("unexpected selected product: %#v", product)
	}
}

func TestShoppingRequestGuard(t *testing.T) {
	if !looksLikeShoppingRequest("2 kg de cualquier cosa") {
		t.Fatal("quantity and unit should be accepted")
	}
	if looksLikeShoppingRequest("escribí un poema sobre el sol") {
		t.Fatal("unrelated prompt should be rejected")
	}
}
