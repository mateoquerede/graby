package carrefour

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"
)

const baseURL = "https://www.carrefour.com.ar"

type Client struct {
	http        *http.Client
	base        string
	orderFormID string
	email       string
	debug       bool
}

func New() *Client {
	jar, _ := cookiejar.New(nil)
	return &Client{base: baseURL, http: &http.Client{Jar: jar, Timeout: 45 * time.Second}}
}

func (c *Client) SetDebug(debug bool) { c.debug = debug }

// Bootstrap seeds an orderForm (the VTEX cart) and keeps its id for the whole
// job. All cart mutations mutate this orderForm. It also attaches the
// `split-cart` and `region-data` customData apps: the store's checkout JS reads
// `orderForm.customData.customApps` and redirects to the home page (losing the
// cart) if either is missing.
//
//   - `split-cart`: `wr()` reads `customData.customApps` for a `split-cart` app;
//     if `customData` is null it throws "can't access property customApps,
//     customData is null" and redirects home.
//   - `region-data`: `wi()` reads `customData.customApps` for a `region-data`
//     app; if absent it shows "Antes de continuar, por favor seleccioná tu método
//     de entrega" and redirects to `?closeCheckout` (the infinite refresh loop).
//
// Both are idempotent PUTs.
func (c *Client) Bootstrap(ctx context.Context) error {
	payload, err := c.request(ctx, http.MethodGet, c.base+"/api/checkout/pub/orderForm", nil, nil)
	if err != nil {
		return err
	}
	var response struct {
		OrderFormID string `json:"orderFormId"`
	}
	if err := json.Unmarshal(payload, &response); err != nil {
		return fmt.Errorf("respuesta de orderForm inválida: %w", err)
	}
	if response.OrderFormID == "" {
		return fmt.Errorf("Carrefour no devolvió un orderFormId")
	}
	c.orderFormID = response.OrderFormID
	if c.debug {
		log.Printf("[carrefour] bootstrap: orderFormId=%s", c.orderFormID)
	}
	// Seed the split-cart customData app so the checkout JS doesn't throw on a
	// null customData and redirect home. This is idempotent.
	app := map[string]any{"mainOrderForm": c.orderFormID}
	body, _ := json.Marshal(app)
	if _, err := c.request(ctx, http.MethodPut, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID+"/customData/split-cart", bytes.NewReader(body), jsonHeaders()); err != nil {
		return err
	}
	// Seed the region-data custom-app so the checkout JS doesn't show the
	// "seleccioná tu método de entrega" modal and redirect to ?closeCheckout
	// (the infinite refresh loop). salesChannel "1" is the default store.
	if err := c.seedRegionData(ctx); err != nil {
		return err
	}
	return nil
}

// seedRegionData attaches the `region-data` customData app (salesChannel +
// regionId) that the checkout's `wi()` function requires. Without it the
// checkout shows "Antes de continuar, por favor seleccioná tu método de
// entrega" and redirects to ?closeCheckout, looping forever.
func (c *Client) seedRegionData(ctx context.Context) error {
	sc := map[string]any{"value": "1"}
	body, _ := json.Marshal(sc)
	if _, err := c.request(ctx, http.MethodPut, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID+"/customData/region-data/salesChannel", bytes.NewReader(body), jsonHeaders()); err != nil {
		return err
	}
	region := map[string]any{"value": "null"}
	body, _ = json.Marshal(region)
	if _, err := c.request(ctx, http.MethodPut, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID+"/customData/region-data/regionId", bytes.NewReader(body), jsonHeaders()); err != nil {
		return err
	}
	return nil
}

// Login runs the VTEX ID classic flow: startlogin to seed the session, then
// classic/validate with the credentials. Both use multipart/form-data bodies
// (the store's react-vtexid bundle serializes them as FormData) and the
// vtex-id-ui-version header. Carrefour AR may force captcha/MFA; if so this
// returns an error and the worker reports the login failure.
func (c *Client) Login(ctx context.Context, email, password string) error {
	if c.debug {
		log.Printf("[carrefour] login: email=%s password_len=%d", email, len(password))
	}
	c.email = email
	// Step 1: startlogin seeds the session (accountName, scope, returnUrl,
	// callbackUrl, user, fingerprint). The response body is empty on success.
	// For the STORE scope, VTEX expects the scope to be the accountName.
	start, startCT := multipartForm(map[string]string{
		"accountName": "carrefourar",
		"scope":       "carrefourar",
		"returnUrl":   c.base + "/",
		"callbackUrl": c.base + "/api/vtexid/pub/authentication/oauthcallback",
		"user":        email,
		"fingerprint": "",
	})
	if _, err := c.request(ctx, http.MethodPost, c.base+"/api/vtexid/pub/authentication/startlogin", start, vtexIDHeaders(startCT)); err != nil {
		return err
	}
	// Step 2: validate the password for the given identifier.
	validate, validateCT := multipartForm(map[string]string{
		"login":          email,
		"password":       password,
		"recaptcha":      "",
		"fingerprint":    "",
		"recaptchaToken": "",
	})
	validateData, err := c.request(ctx, http.MethodPost, c.base+"/api/vtexid/pub/authentication/classic/validate", validate, vtexIDHeaders(validateCT))
	if err != nil {
		return err
	}
	var validateResponse struct {
		AuthStatus        string `json:"authStatus"`
		AuthCookie        cookie `json:"authCookie"`
		AccountAuthCookie cookie `json:"accountAuthCookie"`
	}
	if err := json.Unmarshal(validateData, &validateResponse); err != nil {
		return fmt.Errorf("respuesta de validación inválida: %w", err)
	}
	if validateResponse.AuthStatus != "Success" {
		return fmt.Errorf("credenciales inválidas")
	}
	// Persist the auth cookies so subsequent cart calls are authenticated.
	c.setCookie(validateResponse.AuthCookie)
	c.setCookie(validateResponse.AccountAuthCookie)
	if c.debug {
		log.Printf("[carrefour] login: ok")
	}
	return nil
}

// cookie is the VTEX auth cookie shape returned by classic/validate.
type cookie struct {
	Name  string `json:"Name"`
	Value string `json:"Value"`
}

// setCookie stores a VTEX auth cookie in the client's cookie jar for the
// carrefour.com.ar domain.
func (c *Client) setCookie(ck cookie) {
	if ck.Name == "" || ck.Value == "" {
		return
	}
	host, err := url.Parse(c.base)
	if err != nil {
		return
	}
	c.http.Jar.SetCookies(host, []*http.Cookie{{Name: ck.Name, Value: ck.Value, Path: "/", Domain: host.Hostname()}})
}

// EnsureDeliveryAddress selects a shipping address on the orderForm. VTEX has
// no changeDeliveryAddress actor like Coto; the address is attached via the
// shippingData attachment. The user's saved addresses only populate the
// orderForm once the clientProfileData attachment (with the email) is set, so
// we attach it first, then pick the first available address.
func (c *Client) EnsureDeliveryAddress(ctx context.Context) error {
	if c.orderFormID == "" {
		if err := c.Bootstrap(ctx); err != nil {
			return err
		}
	}
	// Attach the profile so VTEX loads the user's saved addresses.
	if c.email != "" {
		profile := map[string]any{"email": c.email}
		body, _ := json.Marshal(profile)
		if _, err := c.request(ctx, http.MethodPost, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID+"/attachments/clientProfileData", bytes.NewReader(body), jsonHeaders()); err != nil {
			return err
		}
	}
	// Read the orderForm to get the user's saved addresses.
	data, err := c.request(ctx, http.MethodGet, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID, nil, nil)
	if err != nil {
		return err
	}
	var orderForm struct {
		ShippingData struct {
			AvailableAddresses []map[string]any `json:"availableAddresses"`
			SelectedAddresses  []map[string]any `json:"selectedAddresses"`
		} `json:"shippingData"`
	}
	if err := json.Unmarshal(data, &orderForm); err != nil {
		return fmt.Errorf("respuesta de orderForm inválida: %w", err)
	}
	// If an address is already selected, nothing to do.
	if len(orderForm.ShippingData.SelectedAddresses) > 0 {
		return nil
	}
	addresses := orderForm.ShippingData.AvailableAddresses
	// No saved address is NOT fatal: adding items to the cart doesn't need a
	// delivery address — the user picks it at checkout. Failing here would
	// abort the whole job and leave the cart empty.
	if len(addresses) == 0 {
		if c.debug {
			log.Printf("[carrefour] ensureDeliveryAddress: no saved addresses, skipping (user picks at checkout)")
		}
		return nil
	}
	payload := map[string]any{"selectedAddresses": []any{addresses[0]}}
	body, _ := json.Marshal(payload)
	if _, err := c.request(ctx, http.MethodPost, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID+"/attachments/shippingData", bytes.NewReader(body), jsonHeaders()); err != nil {
		return err
	}
	return nil
}

// SelectDelivery ensures a delivery address is selected on the orderForm and
// then picks the first available delivery method (SLA) for each cart item. This
// runs AFTER items are added to the cart (the worker calls it after the item
// loop), because logisticsInfo is only populated once the cart has items and an
// address is selected.
//
// EnsureDeliveryAddress runs BEFORE items are added, when VTEX hasn't loaded the
// user's saved addresses yet (availableAddresses is empty), so it skips. By the
// time SelectDelivery runs the cart has items, so we attach the profile again to
// load the saved addresses, select the first one, and then the SLAs populate.
//
// The checkout JS reads `shippingData.logisticsInfo[].selectedSla` and calls
// `.match()` on it — if it's null the page throws "can't access property match,
// n.selectedSla is null" and redirects to the home page (losing the cart). So
// we must set `selectedSla`/`selectedDeliveryChannel`/`addressId`/`itemIndex`
// on each logisticsInfo item in the shippingData attachment. Posting
// `selectedDeliveryOptions` (the newer VTEX shape) is ignored by this store's
// checkout, so the SLA never persists.
func (c *Client) SelectDelivery(ctx context.Context) error {
	// Ensure an address is selected now that the cart has items. Attach the
	// profile so VTEX loads the user's saved addresses, then pick the first.
	if err := c.ensureDelivery(ctx); err != nil {
		return err
	}
	data, err := c.request(ctx, http.MethodGet, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID, nil, nil)
	if err != nil {
		return err
	}
	var orderForm struct {
		ShippingData struct {
			SelectedAddresses []map[string]any `json:"selectedAddresses"`
			LogisticsInfo     []struct {
				ItemIndex int `json:"itemIndex"`
				SLAs      []struct {
					ID              string `json:"id"`
					DeliveryChannel string `json:"deliveryChannel"`
				} `json:"slas"`
			} `json:"logisticsInfo"`
		} `json:"shippingData"`
	}
	if err := json.Unmarshal(data, &orderForm); err != nil {
		return fmt.Errorf("respuesta de orderForm inválida: %w", err)
	}
	// The addressId the SLAs are quoted against comes from the selected address.
	addressID := ""
	if len(orderForm.ShippingData.SelectedAddresses) > 0 {
		addressID = fmt.Sprint(orderForm.ShippingData.SelectedAddresses[0]["addressId"])
	}
	// Pick the first available SLA for each cart item.
	logistics := make([]any, 0, len(orderForm.ShippingData.LogisticsInfo))
	for _, item := range orderForm.ShippingData.LogisticsInfo {
		if len(item.SLAs) == 0 {
			continue
		}
		sla := item.SLAs[0]
		logistics = append(logistics, map[string]any{
			"itemIndex":               item.ItemIndex,
			"addressId":               addressID,
			"selectedSla":             sla.ID,
			"selectedDeliveryChannel": sla.DeliveryChannel,
		})
	}
	if len(logistics) == 0 {
		if c.debug {
			log.Printf("[carrefour] selectDelivery: no delivery options available, skipping (user picks at checkout)")
		}
		return nil
	}
	payload := map[string]any{"logisticsInfo": logistics}
	body, _ := json.Marshal(payload)
	if _, err := c.request(ctx, http.MethodPost, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID+"/attachments/shippingData", bytes.NewReader(body), jsonHeaders()); err != nil {
		return err
	}
	return nil
}

// ensureDelivery selects the first saved address on the orderForm if none is
// selected yet. It attaches the profile (so VTEX loads the user's saved
// addresses) and then picks the first available address. Unlike
// EnsureDeliveryAddress, this is called when the cart already has items, so
// availableAddresses is populated. No saved address is NOT fatal — the user
// picks it at checkout.
func (c *Client) ensureDelivery(ctx context.Context) error {
	if c.email != "" {
		profile := map[string]any{"email": c.email}
		body, _ := json.Marshal(profile)
		if _, err := c.request(ctx, http.MethodPost, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID+"/attachments/clientProfileData", bytes.NewReader(body), jsonHeaders()); err != nil {
			return err
		}
	}
	data, err := c.request(ctx, http.MethodGet, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID, nil, nil)
	if err != nil {
		return err
	}
	var orderForm struct {
		ShippingData struct {
			AvailableAddresses []map[string]any `json:"availableAddresses"`
			SelectedAddresses  []map[string]any `json:"selectedAddresses"`
		} `json:"shippingData"`
	}
	if err := json.Unmarshal(data, &orderForm); err != nil {
		return fmt.Errorf("respuesta de orderForm inválida: %w", err)
	}
	if len(orderForm.ShippingData.SelectedAddresses) > 0 {
		return nil
	}
	addresses := orderForm.ShippingData.AvailableAddresses
	if len(addresses) == 0 {
		if c.debug {
			log.Printf("[carrefour] ensureDelivery: no saved addresses, skipping (user picks at checkout)")
		}
		return nil
	}
	payload := map[string]any{"selectedAddresses": []any{addresses[0]}}
	body, _ := json.Marshal(payload)
	if _, err := c.request(ctx, http.MethodPost, c.base+"/api/checkout/pub/orderForm/"+c.orderFormID+"/attachments/shippingData", bytes.NewReader(body), jsonHeaders()); err != nil {
		return err
	}
	return nil
}

// Search queries the REST catalog (no auth) and returns a payload normalized to
// the worker's expected shape (response.results[].data) so chooseProduct can
// pick the best match.
func (c *Client) Search(ctx context.Context, query string) (map[string]any, error) {
	endpoint := c.base + "/api/catalog_system/pub/products/search/" + url.PathEscape(query) + "?_from=0&_to=19"
	data, err := c.request(ctx, http.MethodGet, endpoint, nil, nil)
	if err != nil {
		return nil, err
	}
	var products []map[string]any
	if err := json.Unmarshal(data, &products); err != nil {
		return nil, err
	}
	results := make([]any, 0, len(products))
	for _, product := range products {
		items, _ := product["items"].([]any)
		if len(items) == 0 {
			continue
		}
		item, _ := items[0].(map[string]any)
		if item == nil {
			continue
		}
		sellers, _ := item["sellers"].([]any)
		price := any(nil)
		available := false
		if len(sellers) > 0 {
			if seller, ok := sellers[0].(map[string]any); ok {
				if offer, ok := seller["commertialOffer"].(map[string]any); ok {
					price = offer["Price"]
					// Only surface items that are actually in stock, otherwise
					// chooseProduct picks a match that can't be added to the cart.
					if isAvailable, ok := offer["IsAvailable"].(bool); ok {
						available = isAvailable
					}
				}
			}
		}
		if !available {
			continue
		}
		results = append(results, map[string]any{"data": map[string]any{
			"id":                 fmt.Sprint(product["productId"]),
			"sku_id":             fmt.Sprint(item["itemId"]),
			"sku_plu":            fmt.Sprint(product["productId"]),
			"sku_display_name":   fmt.Sprint(product["productName"]),
			"product_list_price": price,
		}})
	}
	return map[string]any{"response": map[string]any{"results": results}}, nil
}

// AddItem adds a SKU to the orderForm via the standard VTEX checkout items
// API. Unlike the persisted GraphQL addToCart mutation, this endpoint needs no
// sha256Hash, so it never breaks when the store redeploys and rotates the hash.
// The response is the updated orderForm; the worker reads the total from it.
func (c *Client) AddItem(ctx context.Context, productID, skuID string, quantity float64) error {
	if c.orderFormID == "" {
		if err := c.Bootstrap(ctx); err != nil {
			return err
		}
	}
	body := map[string]any{
		"orderItems": []any{map[string]any{"id": skuID, "quantity": quantity, "seller": "1"}},
	}
	payload, _ := json.Marshal(body)
	endpoint := c.base + "/api/checkout/pub/orderForm/" + c.orderFormID + "/items"
	data, err := c.request(ctx, http.MethodPost, endpoint, bytes.NewReader(payload), jsonHeaders())
	if err != nil {
		return err
	}
	var response struct {
		OrderFormID string `json:"orderFormId"`
	}
	if json.Unmarshal(data, &response) == nil && response.OrderFormID != "" {
		c.orderFormID = response.OrderFormID
	}
	return nil
}

// CartURL returns the checkout URL bound to the worker's orderForm. VTEX loads
// the cart identified by orderFormId even from a fresh browser session, so the
// user's browser shows the exact cart the worker built. The orderFormId must be
// a query parameter BEFORE the #/cart hash — VTEX checkout reads it from the
// query string, not from inside the fragment. Putting it after the hash makes
// the SPA ignore it and load an empty cart.
func (c *Client) CartURL() string {
	if c.orderFormID == "" {
		return c.base + "/checkout#/cart"
	}
	return c.base + "/checkout?orderFormId=" + c.orderFormID + "#/cart"
}

// OrderFormID returns the current orderForm (cart) id, used by the frontend to
// bind the browser's VTEX cart cookie to the worker's cart.
func (c *Client) OrderFormID() string { return c.orderFormID }

func (c *Client) request(ctx context.Context, method, endpoint string, body io.Reader, headers http.Header) ([]byte, error) {
	request, err := http.NewRequestWithContext(ctx, method, endpoint, body)
	if err != nil {
		return nil, err
	}
	request.Header.Set("User-Agent", "Mozilla/5.0")
	request.Header.Set("Accept", "application/json")
	if headers != nil {
		for key, values := range headers {
			for _, value := range values {
				request.Header.Set(key, value)
			}
		}
	}
	response, err := c.http.Do(request)
	if err != nil {
		if c.debug {
			log.Printf("[carrefour] request %s %s error: %v", method, endpoint, err)
		}
		return nil, err
	}
	defer response.Body.Close()
	data, _ := io.ReadAll(io.LimitReader(response.Body, 4<<20))
	if c.debug {
		// Truncate huge bodies (JS bundles, catalog pages) so debug logs don't
		// flood with megabytes of script content.
		body := string(data)
		if len(body) > 2000 {
			body = body[:2000] + fmt.Sprintf("... (%d bytes total)", len(data))
		}
		log.Printf("[carrefour] request %s %s -> %d body=%s", method, endpoint, response.StatusCode, body)
	}
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return nil, fmt.Errorf("Carrefour HTTP %d: %s", response.StatusCode, string(data))
	}
	return data, nil
}

func jsonHeaders() http.Header {
	header := http.Header{}
	header.Set("Content-Type", "application/json")
	return header
}

// vtexIDHeaders mirrors the store's react-vtexid bundle: it sends the
// vtex-id-ui-version header and the multipart Content-Type on every VTEX call.
func vtexIDHeaders(contentType string) http.Header {
	header := http.Header{}
	header.Set("vtex-id-ui-version", "vtex.react-vtexid@4.70.0")
	if contentType != "" {
		header.Set("Content-Type", contentType)
	}
	return header
}

// multipartForm builds a multipart/form-data body from the given fields,
// matching how the store's react-vtexid bundle serializes its login payloads.
// It returns the body and the Content-Type header (with boundary).
func multipartForm(fields map[string]string) (*bytes.Buffer, string) {
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	for key, value := range fields {
		_ = writer.WriteField(key, value)
	}
	_ = writer.Close()
	return body, writer.FormDataContentType()
}

// parsePrice mirrors worker.parsePrice for the REST catalog Price field.
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
