# Carrefour integration (VTEX)

Status: **IMPLEMENTED** — `client.go` mirrors the `coto.Client` interface and is
driven by the worker via `GRABY_PROVIDER=carrefour`. This doc is the analysis
of how the integration works, written from real network captures of
`carrefour.com.ar` taken manually in a browser (search page + `addToCart`
GraphQL mutation).

Carrefour Argentina runs on **VTEX** (IO + Checkout). That means a very
different session, search and cart model than the Coto ATG/Oracle integration
(`internal/integrations/coto`). Read that package first — this integration
should mirror its public interface.

---

## Interface contract (mirror `coto.Client`)

Implement a `carrefour.Client` with the same shape so `internal/worker/worker.go`
can drive it. The worker pipeline is: `Bootstrap` -> `Login` -> address ->
per-task `Search` -> `AddItem`, then read total via `CartURL`.

```go
type Client struct { ... }
func New() *Client                        // no API key today
func (c *Client) SetDebug(bool)
func (c *Client) Bootstrap(ctx) error     // get/seed orderForm + session cookies
func (c *Client) Login(ctx, email, password) error
func (c *Client) EnsureDeliveryAddress(ctx) error
func (c *Client) Search(ctx, query) (map[string]any, error) // raw payload
func (c *Client) AddItem(ctx, productID, skuID string, quantity float64) error
func (c *Client) CartURL() string
```

The product `Search` decides the best match (rich `params` — a richer payload
helps `chooseProduct` in `worker.go`), specifically `ProductID`/`SKUID` and
`Price`. `worker.go` then calls `AddItem(ProductID, SKUID, qty)`.

---

## Key primitives of VTEX

- **Account**: `carrefourar` (store domain `store`, default workspace `master`).
- **Session**: cookies (`VtexIdclientAutCookie`), a `session` cookie, and the
  **`orderForm`** — the single source of truth for the cart. All cart mutations
  mutate the orderForm. Its `orderFormId` must be threaded through every call.
- **API base**: `https://www.carrefour.com.ar`.

---

## 1. Bootstrap / orderForm 🌟 do this first

The cart lives in an **orderForm**. Before any cart op you need one.

```
GET https://www.carrefour.com.ar/api/checkout/pub/orderForm
```

Response: `{ "orderFormId": "...", "items": [], "totalizers": [], ... }`.

- Keep the `orderFormId` and reuse it for the whole job.
- If empty items, seed it (see AddItem) — items accumulate on the same orderForm.
- Headers: send the same cookies + `User-Agent` you captured; otherwise VTEX
  may issue a new orderFormId each time.

**Total**: `totalizers[].value` is in **centavos** (divide by 100). e.g.
`value: 1158000` = `$11.580,00`.

---

## 2. Login — ⚠️ HIGHEST RISK, verify captcha first

The captured `addToCart` response had `loggedIn: true` + `userProfileId`
because the browser already had a session cookie. The worker starts with *no*
session, so it needs the VTEX ID flow:

```
POST https://www.carrefour.com.ar/api/vtexid/...   (multi-step)
```

- VTEX ID is a **multi-step protocol** (send identifier → receive passcode →
  validate). Not a single form post like Coto's `login`.
- **Captcha risk**: Carrefour AR often forces reCAPTCHA or MFA on login.
  **Do a manual browser login test BEFORE building this.** If captcha is
  mandatory, server-side automation is impractical for this integration.

Mitigation if blocked: support a "resume existing session" path where the user
provides cookies / a pre-authenticated orderForm instead of credentials.

### Delivery address
No `changeDeliveryAddress` like Coto. Set it explicitly on the orderForm via
`updateOrderFormShipping`:

```
POST https://www.carrefour.com.ar/api/checkout/pub/orderForm/{orderFormId}/attachments/shippingData
```

---

## 3. Search — MEDIUM, prefer catalog REST

Captured page: route `store.search`, `query{map:"ft", _q:"coca cola"}`. The
frontend uses a **persisted GraphQL** query, but the **REST catalog** is more
stable and needs no auth:

```
GET https://www.carrefour.com.ar/api/catalog_system/pub/products/search/{query}
   ?_from=0&_to=19
```

Map each result to `models.Product`:

| Carrefour/VTEX field      | `models.Product` field |
|---------------------------|------------------------|
| `productId`               | `ProductID`            |
| `items[0].itemId`         | `SKUID`                |
| `items[0].seller`         | `seller` link (for AddItem) |
| `productName`             | `Name`                 |
| `items[0].sellers[0].commertialOffer.Price` | `Price` (already in ARS) |
| `productLink`/`productImage` | `PLU` / display |

Fallback if REST is closed: the persisted GraphQL query under
`_v/private/graphql/v1` — but its hash (`sha256Hash`) changes on every app
deploy, so you must **rediscover it at runtime from the JS bundle**, exactly
like Coto's `discoverSearchKey`. Prefer REST to avoid that churn.

---

## 4. AddItem — MEDIUM-HIGH, the critical mutation

Captured mutation:

```
POST https://www.carrefour.com.ar/_v/private/graphql/v1
  ?workspace=master&maxAge=long&appsEtag=remove&domain=store&locale=es-AR
Content-Type: application/json

body {
  "operationName": "addToCart",
  "variables": {
    "items": [ { "id": 11187, "quantity": 1, "seller": "1", "options": [] } ],
    "marketingData": {},
    "allowedOutdatedData": [ "paymentData" ]
  },
  "persistedQuery": {
    "version": 1,
    "sha256Hash": "a63161354718146c4282079551df81aaa8fa3d59584520cf5ea1c278fac0db33"
  }
}
```

- `id` = **skuId** (NOT productId). `seller` = VTEX seller id (`"1"`).
- `sha256Hash`: hash of the addCart query. **Rotates on every app deploy.**
  Rediscover it from the store's JS bundle at runtime (cache it per-process,
  re-discover on failure).
- The persisted GraphQL mutuales the orderForm — the response is the updated
  `OrderForm`. Extract `totalizers` or the worker's own sum for the total.
- The response's `data.addToCart` is the orderForm (`OrderForm` type).

### Checkout URL
`https://www.carrefour.com.ar/checkout#/cart` (confirm exact path in browser).

---

## Known pitfalls / gotchas

1. **Login captcha** — validate before building (see §2).
2. **Persisted query hash drift** — never hardcode long-term; rediscover like Coto.
3. **orderForm identity** — losing the id = scattered cart. Keep one per job,
   store it alongside cookies.
4. **Prices are centavos** in `totalizers` (÷100) but already dollars in the
   REST catalog `commertialOffer.Price`.
5. **Seller id** — always `"1"` in captures; respect whatever the search returns.
6. **Locale** — `es-AR`, `domain=store`. Use `workspace=master`.

---

## Suggested implementation order

1. ✅ Log in manually in a browser → confirm **no mandatory captcha** (else stop here).
2. `New` + `request` helper + cookie jar (port from `coto`).
3. `Bootstrap`: GET orderForm, store `orderFormId`.
4. `Search`: REST catalog → map to `models.Product`. Validate with one query.
5. `AddItem`: GraphQL addToCart with runtime-discovered hash; verify items accumulate.
6. `Login` + `updateOrderFormShipping` for address.
7. `CartURL` + total.
8. Unit tests with recorded payloads (mirror `coto` tests: parse-only, no live calls).