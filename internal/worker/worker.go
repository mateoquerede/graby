package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"graby/internal/config"
	"graby/internal/coto"
	"graby/internal/guard"
	"graby/internal/models"
	"graby/internal/openrouter"
	"graby/internal/store"
)

type Worker struct {
	repo *store.Repository
	cfg  config.Config
	llm  *openrouter.Client
}

func New(repo *store.Repository, cfg config.Config) *Worker {
	return &Worker{repo: repo, cfg: cfg, llm: openrouter.New(cfg.OpenRouterKey, cfg.OpenRouterModel, cfg.OpenRouterModels, cfg.OpenRouterBaseURL, cfg.OpenRouterTimeout)}
}

func (w *Worker) Run(ctx context.Context) error {
	if err := w.repo.RecoverStale(ctx, 15*time.Minute); err != nil {
		return err
	}
	log.Print("worker listening for jobs")
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()
	for {
		if err := w.repo.RecoverStale(ctx, 15*time.Minute); err != nil {
			log.Printf("recover stale jobs: %v", err)
		}
		job, err := w.repo.Claim(ctx)
		if err != nil {
			log.Printf("claim job: %v", err)
		}
		if job != nil {
			log.Printf("processing job %s", job.ID)
			w.process(ctx, job)
			log.Printf("done job %s", job.ID)
			continue
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
		}
	}
}

func (w *Worker) process(ctx context.Context, job *models.Job) {
	publish := func(status, message string, extra map[string]any) {
		if err := w.repo.Publish(ctx, job.ID, status, message, extra); err != nil {
			log.Printf("publish %s for %s: %v", status, job.ID, err)
		}
	}
	publish("STARTING", "Procesando tu pedido...", nil)
	publish("INTERPRETING_REQUEST", "Entendiendo tu pedido...", nil)
	tasks := job.Payload.ConfirmedTasks
	if len(tasks) == 0 {
		var err error
		tasks, err = w.plan(ctx, job.Payload.Message, job.Payload.CorrectionMode, job.Payload.PreviousTasks)
		if err != nil {
			publish(models.StatusFailed, err.Error(), nil)
			return
		}
	}
	if len(tasks) == 0 {
		publish(models.StatusFailed, "No pude interpretar productos en tu pedido.", nil)
		return
	}
	publish("INTERPRETED", fmt.Sprintf("Separé tu pedido en %d producto(s) para buscar.", len(tasks)), map[string]any{"item_count": len(tasks), "items": queries(tasks)})
	if len(job.Payload.ConfirmedTasks) == 0 {
		publish(models.StatusAwaitingConfirmation, "Entendí tu pedido y armé esta lista. ¿Está bien? Confirmala para comenzar la búsqueda o enviame una corrección.", map[string]any{"items": tasks})
		return
	}

	client := coto.New(w.cfg.CotoSearchKey)
	client.SetDebug(w.cfg.Debug)
	if err := client.Bootstrap(ctx); err != nil {
		publish(models.StatusFailed, safeExternalError(err), nil)
		return
	}
	publish("AUTHENTICATING", "Iniciando sesión...", nil)
	if err := client.Login(ctx, job.Payload.Email, job.Payload.Password); err != nil {
		publish(models.StatusFailed, "No pude iniciar sesión. Verificá tus credenciales e intentá nuevamente.", nil)
		return
	}
	publish("AUTHENTICATED", "Sesión iniciada correctamente.", nil)
	if err := client.EnsureDeliveryAddress(ctx); err != nil {
		publish(models.StatusFailed, safeExternalError(err), nil)
		return
	}
	publish("SEARCHING_PRODUCTS", "Voy a buscar cada producto y comparar las opciones disponibles.", nil)
	selected := make([]models.Product, 0, len(tasks))
	for _, task := range tasks {
		publish("SEARCHING_PRODUCTS", fmt.Sprintf(`Buscando "%s"...`, task.Query), nil)
		payload, err := client.Search(ctx, task.Query)
		if err != nil {
			publish("PRODUCT_ERROR", fmt.Sprintf(`⚠️ Error buscando "%s": %s`, task.Query, safeExternalError(err)), map[string]any{"requested": task.Query})
			continue
		}
		publish("COMPARING_OPTIONS", fmt.Sprintf(`Comparando opciones para "%s"...`, task.Query), nil)
		product, err := chooseProduct(task, payload)
		if err != nil {
			publish("PRODUCT_NOT_FOUND", fmt.Sprintf(`⚠️ No encontré un producto que coincida con "%s".`, task.Query), map[string]any{"requested": task.Query})
			continue
		}
		if err = client.AddItem(ctx, product.ProductID, product.SKUID, task.Quantity); err != nil {
			publish("PRODUCT_ERROR", fmt.Sprintf(`⚠️ Error buscando "%s": %s`, task.Query, safeExternalError(err)), map[string]any{"requested": task.Query})
			continue
		}
		selected = append(selected, product)
		publish("PRODUCT_ADDED", fmt.Sprintf("Encontré una buena coincidencia y la sumé al carrito: %sx %s.", quantityText(task.Quantity), product.Name), map[string]any{"product": product})
	}
	publish("REVIEWING_CART", "Revisando los productos seleccionados...", nil)
	total := 0.0
	for _, product := range selected {
		total += product.Price * product.Quantity
	}
	publish("CALCULATING_TOTAL", "Calculando el total estimado...", nil)
	publish("PREPARING_CART", "Preparando tu carrito...", nil)
	publish(models.StatusCompleted, "Listo. Preparé tu carrito. Revisá los productos y completá el pago.", map[string]any{"items": selected, "total": total, "checkout_url": client.CartURL()})
}

func (w *Worker) plan(ctx context.Context, prompt string, correction bool, previous []models.Task) ([]models.Task, error) {
	if strings.TrimSpace(prompt) == "" {
		return nil, fmt.Errorf("El pedido está vacío.")
	}
	if len([]rune(prompt)) > 500 {
		return nil, fmt.Errorf("El pedido supera el límite de 500 caracteres.")
	}
	if guard.Injection(prompt) {
		return nil, fmt.Errorf("El pedido contiene instrucciones no permitidas.")
	}
	if !correction && !guard.LooksLikeShoppingRequest(prompt) {
		return nil, fmt.Errorf("Solo puedo ayudarte a armar un carrito de compras.")
	}
	if !correction {
		items := parsePrompt(prompt)
		if len(items) > 0 {
			return validateTasks(items)
		}
	}
	request := "Convertí pedido de compra de usuario en lista JSON. Respondé SOLO con un objeto JSON con clave items. Cada item requiere query en español singular y quantity >= 1. No agregues productos. Pedido: " + prompt
	if correction {
		request += "\nLista actual: " + jsonString(previous) + "\nAplicá la corrección y conservá los productos no modificados."
	}
	raw, err := w.llm.CompleteJSON(ctx, []openrouter.Message{{Role: "system", Content: "Sos generador estricto de JSON para listas de compra. Respondé sólo JSON válido."}, {Role: "user", Content: request}}, 512, 0)
	if err != nil {
		return nil, err
	}
	items, err := parseLLMTasks(raw)
	if err != nil {
		return nil, fmt.Errorf("No pude interpretar productos en tu pedido.")
	}
	return validateTasks(items)
}

func parsePrompt(value string) []models.Task {
	parts := regexp.MustCompile(`(?i)\s*(?:,|;|\n|\s+y\s+|\s+e\s+)\s*`).Split(value, -1)
	items := make([]models.Task, 0, len(parts))
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		quantity := quantityFrom(part)
		query := regexp.MustCompile(`(?i)^\s*(?:\d+(?:[.,]\d+)?|un|una|uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s*(?:(?:litro(?:s)?|kilo(?:s)?|gramo(?:s)?|unidad(?:es)?|botella(?:s)?|caja(?:s)?|pack|kgs|kg|gr|ml|lts|lt|cc|g|l)\s*)?`).ReplaceAllString(part, "")
		query = regexp.MustCompile(`(?i)^\s*(?:de|del|la|las|el|los)\s+`).ReplaceAllString(query, "")
		query = strings.Trim(strings.TrimSpace(query), " ,;.-_")
		query = singular(query)
		if query != "" {
			items = append(items, models.Task{Query: query, Quantity: quantity})
		}
	}
	return items
}

func parseLLMTasks(raw string) ([]models.Task, error) {
	var wrapper struct {
		Items []models.Task `json:"items"`
	}
	if json.Unmarshal([]byte(raw), &wrapper) == nil && len(wrapper.Items) > 0 {
		return wrapper.Items, nil
	}
	var direct []models.Task
	if json.Unmarshal([]byte(raw), &direct) == nil {
		return direct, nil
	}
	start, end := strings.Index(raw, "["), strings.LastIndex(raw, "]")
	if start >= 0 && end > start && json.Unmarshal([]byte(raw[start:end+1]), &direct) == nil {
		return direct, nil
	}
	return nil, fmt.Errorf("invalid AI JSON")
}

func validateTasks(items []models.Task) ([]models.Task, error) {
	if len(items) == 0 {
		return nil, fmt.Errorf("No pude interpretar productos en tu pedido.")
	}
	if len(items) > 20 {
		return nil, fmt.Errorf("El pedido no puede superar 20 productos.")
	}
	for index := range items {
		items[index].Query = strings.Join(strings.Fields(singular(items[index].Query)), " ")
		if items[index].Query == "" || items[index].Quantity < 1 {
			return nil, fmt.Errorf("El pedido contiene productos inválidos.")
		}
		if items[index].Quantity > 50 {
			return nil, fmt.Errorf("La cantidad máxima por producto es 50.")
		}
	}
	return items, nil
}

func chooseProduct(task models.Task, payload map[string]any) (models.Product, error) {
	response, _ := payload["response"].(map[string]any)
	results, _ := response["results"].([]any)
	var candidates []models.Product
	for _, result := range results {
		entry, ok := result.(map[string]any)
		if !ok {
			continue
		}
		data, _ := entry["data"].(map[string]any)
		if data == nil {
			data = entry
		}
		productID, skuID := stringValue(data, "id", "product_id"), stringValue(data, "sku_id", "skuId")
		plu := stringValue(data, "sku_plu", "plu")
		if plu == "" {
			plu = productIDFromID(productID)
		}
		if productID == "" || skuID == "" || plu == "" {
			continue
		}
		name := stringValue(data, "sku_display_name", "product_display_name", "value", "sku_description")
		price, ok := parsePrice(data["product_list_price"])
		if !ok {
			price, ok = parsePrice(data["price"])
		}
		if !ok {
			continue
		}
		candidates = append(candidates, models.Product{Requested: task.Query, Name: name, PLU: plu, Quantity: task.Quantity, Price: price, ProductID: productID, SKUID: skuID, UnitPrice: price / unitAmount(name, stringValue(data, "product_format"))})
	}
	if len(candidates) == 0 {
		return models.Product{}, fmt.Errorf("no candidates")
	}
	sort.SliceStable(candidates, func(i, j int) bool {
		left, right := matchScore(task.Query, candidates[i].Name), matchScore(task.Query, candidates[j].Name)
		if left == right {
			return candidates[i].UnitPrice < candidates[j].UnitPrice
		}
		return left > right
	})
	best := candidates[0]
	if matchScore(task.Query, best.Name) == 0 {
		return models.Product{}, fmt.Errorf("no matching candidates")
	}
	best.Reason = "Mejor coincidencia semántica disponible; el precio normalizado se usó como desempate."
	return best, nil
}

func stringValue(data map[string]any, keys ...string) string {
	for _, key := range keys {
		if value, ok := data[key]; ok && fmt.Sprint(value) != "<nil>" {
			return fmt.Sprint(value)
		}
	}
	return ""
}
func productIDFromID(value string) string {
	found := regexp.MustCompile(`(?i)prod0*([0-9]+)`).FindStringSubmatch(value)
	if len(found) > 1 {
		return found[1]
	}
	return ""
}
func parsePrice(value any) (float64, bool) {
	raw := strings.TrimSpace(strings.TrimPrefix(fmt.Sprint(value), "$"))
	if raw == "" || raw == "<nil>" {
		return 0, false
	}
	if strings.Contains(raw, ",") {
		raw = strings.ReplaceAll(strings.ReplaceAll(raw, ".", ""), ",", ".")
	} else if strings.Count(raw, ".") > 1 || regexp.MustCompile(`\.\d{3}$`).MatchString(raw) {
		raw = strings.ReplaceAll(raw, ".", "")
	}
	valueFloat, err := strconv.ParseFloat(raw, 64)
	return valueFloat, err == nil
}
func unitAmount(name, format string) float64 {
	raw := strings.ToLower(name + " " + format)
	found := regexp.MustCompile(`(\d+(?:[.,]\d+)?)\s*(ml|cc|l|lt|litro|litros|g|gr|gramos|kg|kilo|kilos)\b`).FindStringSubmatch(raw)
	if len(found) < 3 {
		return 1
	}
	value, _ := strconv.ParseFloat(strings.ReplaceAll(found[1], ",", "."), 64)
	switch found[2] {
	case "ml", "cc":
		return value / 1000
	case "g", "gr", "gramos":
		return value / 1000
	}
	return value
}
func matchScore(requested, candidate string) int {
	requestTokens := tokens(requested)
	candidateTokens := tokens(candidate)
	if len(requestTokens) == 0 || len(candidateTokens) == 0 {
		return 0
	}
	normalizedRequest, normalizedCandidate := strings.Join(requestTokens, " "), strings.Join(candidateTokens, " ")
	if normalizedRequest == normalizedCandidate {
		return 100
	}
	if strings.Contains(normalizedCandidate, normalizedRequest) || strings.Contains(normalizedRequest, normalizedCandidate) {
		return 90
	}
	in := map[string]bool{}
	for _, token := range requestTokens {
		in[token] = true
	}
	overlap := 0
	union := map[string]bool{}
	for _, t := range requestTokens {
		union[t] = true
	}
	for _, t := range candidateTokens {
		if in[t] {
			overlap++
		}
		union[t] = true
	}
	return overlap * 100 / len(union)
}
func tokens(value string) []string {
	clean := regexp.MustCompile(`[^\p{L}\p{N}]+`).ReplaceAllString(strings.ToLower(value), " ")
	var result []string
	for _, item := range strings.Fields(clean) {
		if len([]rune(item)) > 2 {
			result = append(result, item)
		}
	}
	return result
}
func singular(value string) string {
	words := strings.Fields(value)
	for i, word := range words {
		lower := strings.ToLower(word)
		if strings.HasSuffix(lower, "ces") && len(lower) > 4 {
			words[i] = word[:len(word)-3] + "z"
		} else if len(lower) > 3 && (strings.HasSuffix(lower, "as") || strings.HasSuffix(lower, "es") || strings.HasSuffix(lower, "is") || strings.HasSuffix(lower, "os") || strings.HasSuffix(lower, "us")) {
			words[i] = word[:len(word)-1]
		}
	}
	return strings.Join(words, " ")
}
func quantityFrom(value string) float64 {
	match := regexp.MustCompile(`\b(\d+(?:[.,]\d+)?)`).FindStringSubmatch(value)
	if len(match) > 1 {
		number, _ := strconv.ParseFloat(strings.ReplaceAll(match[1], ",", "."), 64)
		return math.Max(1, number)
	}
	for word, number := range map[string]float64{"uno": 1, "una": 1, "un": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10} {
		if regexp.MustCompile(`(?i)\b` + word + `\b`).MatchString(value) {
			return number
		}
	}
	return 1
}
func queries(items []models.Task) []string {
	values := make([]string, len(items))
	for i, item := range items {
		values[i] = item.Query
	}
	return values
}
func jsonString(value any) string { data, _ := json.Marshal(value); return string(data) }
func quantityText(value float64) string {
	if value == math.Trunc(value) {
		return strconv.Itoa(int(value))
	}
	return strconv.FormatFloat(value, 'f', -1, 64)
}
func safeExternalError(err error) string {
	text := err.Error()
	if strings.Contains(strings.ToLower(text), "openrouter") {
		return "No se pudo conectar al servicio de IA (OpenRouter). Verificá la API key e intentá nuevamente."
	}
	return "La automatización se detuvo inesperadamente. No se realizó ningún pago."
}
