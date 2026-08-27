package coto

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"regexp"
	"strings"
	"time"
)

const baseURL = "https://www.coto.com.ar"
const searchURL = "https://api.coto.com.ar/api/v1/ms-digital-sitio-bff-web/api/v1/products/search/"

type Client struct {
	http        *http.Client
	base        string
	searchKey   string
	dynSessConf string
	debug       bool
}

func New(searchKey string) *Client {
	jar, _ := cookiejar.New(nil)
	return &Client{searchKey: searchKey, base: baseURL, http: &http.Client{Jar: jar, Timeout: 45 * time.Second}}
}

func (c *Client) SetDebug(debug bool) { c.debug = debug }

func (c *Client) Bootstrap(ctx context.Context) error {
	if c.debug {
		log.Printf("[coto] bootstrap: init request")
	}
	if _, err := c.request(ctx, http.MethodPost, c.base+"/rest/model/atg/actors/cProfileActor/init?pushSite=CotoDigital", nil, nil); err != nil {
		return err
	}
	if c.debug {
		log.Printf("[coto] bootstrap: init ok")
	}
	payload, err := c.request(ctx, http.MethodPost, c.base+"/rest/model/atg/rest/SessionConfirmationActor/getSessionConfirmationNumber?pushSite=CotoDigital", nil, nil)
	if err != nil {
		return err
	}
	if c.debug {
		log.Printf("[coto] bootstrap: confirmation body=%s", string(payload))
	}
	// UseNumber() preserves large integers exactly. The default decoder turns
	// every number into float64, so a 19-digit session token like
	// -7278346090397846952 becomes -7.278346090397847e+18, which Coto rejects
	// as an invalid/expired session.
	decoder := json.NewDecoder(strings.NewReader(string(payload)))
	decoder.UseNumber()
	var response map[string]any
	if err := decoder.Decode(&response); err != nil {
		return err
	}
	token := fmt.Sprint(response["sessionConfirmationNumber"])
	if token == "" || token == "<nil>" {
		return fmt.Errorf("Coto no devolvió un token de sesión")
	}
	c.dynSessConf = token
	if c.debug {
		log.Printf("[coto] bootstrap: dynSessConf=%s", c.dynSessConf)
	}
	return nil
}

func (c *Client) Login(ctx context.Context, email, password string) error {
	if c.debug {
		log.Printf("[coto] login: email=%s password_len=%d", email, len(password))
	}
	form := url.Values{"IsAngular": {"true"}, "login": {email}, "password": {password}}
	data, err := c.actor(ctx, http.MethodPost, "/rest/model/atg/actors/cProfileActor/login", form)
	if err != nil {
		if c.debug {
			log.Printf("[coto] login: request error: %v", err)
		}
		return err
	}
	if c.debug {
		log.Printf("[coto] login: status ok, body=%s", string(data))
	}
	if len(strings.TrimSpace(string(data))) == 0 {
		if c.debug {
			log.Printf("[coto] login: empty response body")
		}
		return nil
	}
	var response map[string]any
	if err := json.Unmarshal(data, &response); err != nil {
		if c.debug {
			log.Printf("[coto] login: invalid JSON: %v", err)
		}
		return fmt.Errorf("respuesta de login inválida: %w", err)
	}
	if c.debug {
		log.Printf("[coto] login: parsed payload=%s", string(data))
	}
	if loginFailed(response) {
		if c.debug {
			log.Printf("[coto] login: rejected (codigoError=%v error=%v success=%v)", response["codigoError"], response["error"], response["success"])
		}
		return fmt.Errorf("credenciales inválidas")
	}
	return nil
}

// loginFailed mirrors the Python worker's login validation. A login only
// succeeds when Coto explicitly reports a numeric/short "0" codigoError with no
// error and success is not false. In particular a null codigoError (or any
// value other than "0") must be treated as a failure, otherwise invalid
// credentials slip through and the worker never reports the login failure.
func loginFailed(response map[string]any) bool {
	if value, present := response["codigoError"]; present {
		if value == nil || fmt.Sprint(value) != "0" {
			return true
		}
	}
	if response["error"] != nil {
		return true
	}
	if success, ok := response["success"].(bool); ok && !success {
		return true
	}
	return false
}

func (c *Client) EnsureDeliveryAddress(ctx context.Context) error {
	data, err := c.actor(ctx, http.MethodGet, "/rest/model/atg/actors/cProfileActor/getDireccionesEntrega", nil)
	if err != nil {
		return err
	}
	var payload map[string]any
	if err := json.Unmarshal(data, &payload); err != nil {
		return err
	}
	addresses, _ := payload["domicilios"].([]any)
	if len(addresses) == 0 {
		if nested, ok := payload["domicilios"].(map[string]any); ok {
			addresses, _ = nested["items"].([]any)
			if len(addresses) == 0 {
				addresses, _ = nested["results"].([]any)
			}
		}
	}
	if len(addresses) == 0 {
		return fmt.Errorf("la cuenta no tiene domicilios de entrega configurados")
	}
	selected, _ := addresses[0].(map[string]any)
	defaultID := fmt.Sprint(payload["defaultShippingAddressId"])
	for _, address := range addresses {
		value, ok := address.(map[string]any)
		if !ok {
			continue
		}
		if addressID(value) == defaultID || isSelected(value) {
			selected = value
			break
		}
	}
	id := addressID(selected)
	if id == "" {
		return fmt.Errorf("Coto no devolvió el identificador del domicilio")
	}
	_, err = c.actorWithParams(ctx, http.MethodGet, "/rest/model/atg/actors/cProfileActor/changeDeliveryAddress", url.Values{"selectedAddress": {id}}, nil)
	return err
}

func (c *Client) Search(ctx context.Context, query string) (map[string]any, error) {
	if c.searchKey == "" {
		key, err := c.discoverSearchKey(ctx)
		if err != nil {
			return nil, err
		}
		c.searchKey = key
	}
	requestURL := searchURL + url.PathEscape(query)
	values := url.Values{"key": {c.searchKey}, "num_results_per_page": {"24"}, "pre_filter_expression": {`{"name":"store_availability","value":"200"}`}, "c": {"cio-fe-web-coto-4.2.0"}, "i": {"c153a437-d12d-4053-a41c-444adf91c32d"}, "s": {"13"}, "origin_referrer": {"/productos/" + query}, "us": {"200"}}
	data, err := c.request(ctx, http.MethodGet, requestURL+"?"+values.Encode(), nil, nil)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	return payload, json.Unmarshal(data, &payload)
}

func (c *Client) AddItem(ctx context.Context, productID, skuID string, quantity float64) error {
	form := url.Values{"cambiaSuc": {"true"}, "prodId": {productID}, "quantity": {trimFloat(quantity)}, "skuId": {skuID}, "sucPickUp": {"null"}}
	data, err := c.actor(ctx, http.MethodPost, "/rest/model/atg/actors/cCarritoActor/addOrRemoveItemToOrderV2", form)
	if err != nil {
		return err
	}
	var payload map[string]any
	if json.Unmarshal(data, &payload) == nil && fmt.Sprint(payload["codigoError"]) != "<nil>" && fmt.Sprint(payload["codigoError"]) != "0" {
		return fmt.Errorf("%v", payload["mensajeError"])
	}
	return nil
}

func (c *Client) CartURL() string { return c.base + "/sitios/cdigi/carrito" }

// SelectDelivery is a no-op for Coto: ATG selects the delivery method as part
// of the checkout flow, so there's nothing to pre-select here.
func (c *Client) SelectDelivery(ctx context.Context) error { return nil }

// OrderFormID is a no-op for Coto (it has no VTEX orderForm); the worker only
// uses it to bind the browser cart cookie for VTEX-based providers.
func (c *Client) OrderFormID() string { return "" }

func (c *Client) actor(ctx context.Context, method, path string, form url.Values) ([]byte, error) {
	return c.actorWithParams(ctx, method, path, nil, form)
}
func (c *Client) actorWithParams(ctx context.Context, method, path string, params, form url.Values) ([]byte, error) {
	if c.dynSessConf == "" {
		if err := c.Bootstrap(ctx); err != nil {
			return nil, err
		}
	}
	if params == nil {
		params = url.Values{}
	}
	params.Set("pushSite", "CotoDigital")
	params.Set("_dynSessConf", c.dynSessConf)
	return c.request(ctx, method, c.base+path+"?"+params.Encode(), form, nil)
}
func (c *Client) request(ctx context.Context, method, endpoint string, form url.Values, headers http.Header) ([]byte, error) {
	var body io.Reader
	if form != nil {
		body = strings.NewReader(form.Encode())
	}
	request, err := http.NewRequestWithContext(ctx, method, endpoint, body)
	if err != nil {
		return nil, err
	}
	request.Header.Set("User-Agent", "Mozilla/5.0")
	request.Header.Set("Accept", "application/json")
	if form != nil {
		request.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	}
	if headers != nil {
		request.Header = headers
	}
	response, err := c.http.Do(request)
	if err != nil {
		if c.debug {
			log.Printf("[coto] request %s %s error: %v", method, endpoint, err)
		}
		return nil, err
	}
	defer response.Body.Close()
	data, _ := io.ReadAll(io.LimitReader(response.Body, 4<<20))
	if c.debug {
		log.Printf("[coto] request %s %s -> %d body=%s", method, endpoint, response.StatusCode, string(data))
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return nil, fmt.Errorf("Coto HTTP %d: %s", response.StatusCode, string(data))
	}
	return data, nil
}
func (c *Client) discoverSearchKey(ctx context.Context) (string, error) {
	page, err := c.request(ctx, http.MethodGet, c.base+"/", nil, nil)
	if err != nil {
		return "", err
	}
	scripts := regexp.MustCompile(`<script[^>]+src=["']([^"']+)`).FindAllStringSubmatch(string(page), -1)
	keyPattern := regexp.MustCompile(`\b(key_[A-Za-z0-9]+)\b`)
	for _, script := range scripts {
		endpoint, _ := url.Parse(script[1])
		base, _ := url.Parse(baseURL)
		bundleURL := base.ResolveReference(endpoint).String()
		bundle, err := c.request(ctx, http.MethodGet, bundleURL, nil, nil)
		if err != nil {
			continue
		}
		if found := keyPattern.FindStringSubmatch(string(bundle)); len(found) > 1 {
			return found[1], nil
		}
	}
	return "", fmt.Errorf("no se pudo obtener la clave de búsqueda de Coto")
}
func addressID(value map[string]any) string {
	for _, key := range []string{"id", "ID", "idDomicilio", "IDDOMICILIO", "idDireccion", "IDDIRECCION", "idAddress", "IDADDRESS", "address_id", "codigo"} {
		if id := fmt.Sprint(value[key]); id != "" && id != "<nil>" {
			return id
		}
	}
	return ""
}
func isSelected(value map[string]any) bool {
	for _, key := range []string{"selected", "default", "predeterminado", "seleccionado", "SELECCIONADA"} {
		text := strings.ToLower(fmt.Sprint(value[key]))
		if text == "true" || text == "s" || text == "y" || text == "1" {
			return true
		}
	}
	return false
}
func trimFloat(value float64) string {
	return strings.TrimRight(strings.TrimRight(fmt.Sprintf("%.6f", value), "0"), ".")
}
