# Catalog and orders

This guide walks through the whole buying flow:
check your balance, find a product, get its price, place an order, and read the codes.

Related: [Authentication](AUTHENTICATION.md) · [Conventions](CONVENTIONS.md) · [Webhooks](WEBHOOKS.md)

## Account and balance

### Account

`GET /api/v1/account` shows your company details and whether the API is switched on.

```json
{
  "merchant_id": "M00000001",
  "name": "Acme Shop",
  "legal_name": "Acme Shop Ltd",
  "billing_email": "billing@acme.example",
  "status": "active",
  "kyb_status": "approved",
  "api_access_enabled": true,
  "default_currency": "USD",
  "purchase_limits": {
    "currency": "USD",
    "verified": true,
    "max_order_amount": "1000.00",
    "daily_order_amount_limit": "10000.00",
    "daily_order_count_limit": 1000,
    "used_today_amount": "120.50",
    "used_today_count": 3,
    "day_resets_at": "2026-10-01T00:00:00+00:00"
  }
}
```

- `default_currency` is the currency of your wallet. All prices you pay are in it.
- `api_access_enabled` is `true` once CardV has approved your business.

### Balance

`GET /api/v1/balance` shows how much money you can spend.

```json
{
  "currency": "USD",
  "balance": "1520.40",
  "reserved_amount": "0.00",
  "available_balance": "1520.40",
  "low_balance_threshold": "200.00",
  "low_balance_notified_at": null,
  "is_active": true
}
```

- `available_balance` is what you can spend now. It is `balance` minus `reserved_amount`.
- An order larger than `available_balance` is rejected, and nothing is charged.
- `low_balance_threshold` is the level for the low-balance email. You set it in the Portal.
- To add money, use the Portal.

## Products (SKUs)

A **SKU** is one product you can buy, for example "Steam Wallet 10 USD".
Its ID looks like `S000456`. You quote and order SKUs.

`GET /api/v1/skus` lists the SKUs you can buy. Example:

```http
GET /api/v1/skus?search=steam&region=US&limit=50&offset=0
```

Filters (all optional):

| Filter | Example | Matches |
| --- | --- | --- |
| `search` | `steam` | SKU ID, name or brand |
| `brand` | `Steam` | Brand name (any case) |
| `region` | `US` | Country code or country name. `GLC` = global, `EU` = Europe |
| `category` | `Travel` | Business category, for example `Travel`, `Digital Wallets & Payment`, `Game Credits` |
| `vertical` | `gift_card` | Product line |
| `product_type` | `pin_code` | How it is delivered |

Paging: send `limit` (default 100, max 500) and `offset`.
Keep asking with a higher `offset` until `offset` reaches `count`.

```json
{
  "count": 7,
  "limit": 1,
  "results": [
    {
      "sku_id": "S000456",
      "product_id": "P000123",
      "name": "Steam Wallet 10 USD",
      "product_name": "Steam Wallet US",
      "brand": "Steam",
      "region": "US",
      "vertical": "gift_card",
      "product_type": "pin_code",
      "denomination_type": "fixed",
      "denomination_value": "10",
      "face_currency": "USD",
      "merchant_price": "9.25",
      "settlement_currency": "USD",
      "availability": "available",
      "min_quantity": 1,
      "max_quantity": 100,
      "required_input_schema": [],
      "...": "more fields"
    }
  ],
  "filter_options": {"brands": [], "regions": [], "categories": [], "verticals": []}
}
```

`GET /api/v1/skus/{sku_id}` returns one SKU with the same fields.

The most useful fields:

| Field | Meaning |
| --- | --- |
| `sku_id` | The ID you use to quote and order. |
| `merchant_price` | Your price per unit, in `settlement_currency`. |
| `availability` | `available` or `unavailable`. Only order `available` SKUs. |
| `denomination_type` | `fixed` or `range`. See [fixed and range amounts](#fixed-and-range-amounts). |
| `amount_step` | Range SKUs only. The amount must be a multiple of this value, for example `"1"` means whole numbers only. `null` means no step. |
| `face_currency` | Currency printed on the card. May differ from your wallet. |
| `min_quantity`, `max_quantity` | How many units one order line may have. |
| `product_type` | `pin_code` (you get a code) or `direct_charge` (we top up an account). |
| `required_input_schema` | Details you must send for [direct top-ups](#direct-top-ups). |
| `brand_logo_url`, `image_url` | Images hosted by CardV, or `""`. |
| `description`, `redemption_instructions`, `terms` | Text you can show your customers. |

Tips:

- You only see SKUs that are active and open to your account. Other SKUs return 404.
- Sync the SKU list every 5–15 minutes. Always get a quote right before you order.
- `filter_options` lists the brands, regions and product lines you can filter by.

### Sync by product

If your store shows one page per product with an amount picker, sync products instead of SKUs.
`GET /api/v1/products` lists products. Each product carries all the SKUs you can buy in it.

```http
GET /api/v1/products?brand=Steam&region=GB&limit=50&offset=0
```

It takes the same filters and paging as `GET /api/v1/skus`. `count` counts products and `sku_count` counts their SKUs.

```json
{
  "count": 1,
  "sku_count": 4,
  "limit": 50,
  "results": [
    {
      "product_id": "P000123",
      "product_name": "Steam Wallet UK",
      "brand": "Steam",
      "category": "Gaming",
      "region": "GB",
      "product_type": "pin_code",
      "image_url": "https://b2b.cardv.net/api/v1/catalog-assets/steam.png",
      "required_input_schema": [],
      "skus": [
        {
          "sku_id": "S000456",
          "name": "Steam Wallet 5 GBP",
          "label": "5 GBP",
          "denomination_type": "fixed",
          "denomination_value": "5",
          "face_currency": "GBP",
          "merchant_price": "7.61",
          "settlement_currency": "USD",
          "availability": "available",
          "min_quantity": 1,
          "max_quantity": 100,
          "...": "more fields"
        }
      ]
    }
  ],
  "filter_options": {"brands": [], "regions": [], "categories": [], "verticals": []}
}
```

`GET /api/v1/products/{product_id}` returns one product with its SKUs, plus `description`, `redemption_instructions`, `terms` and `disclaimer`.

- Each SKU in `skus` has the same fields and values as in `GET /api/v1/skus`. Quote and order with its `sku_id` as usual.
- Use `label` as the option text, for example `5 GBP` or `Tinder Plus 1 Month`. Some products are plans, not amounts.
- One product has one face currency and one amount type. A range SKU is always a product of its own.
- The list leaves out the long texts. Read them once per product from `GET /api/v1/products/{product_id}`.

### Fixed and range amounts

Most SKUs have a **fixed** face value, such as 10 USD.
Some SKUs have a **range**: your customer chooses the amount, such as 5 to 500 USD.

| Type | When quoting | When ordering |
| --- | --- | --- |
| `fixed` | Send `quantity` | Leave out `amount` |
| `range` | Send `quantity` and `amount` | Send `amount` |

For a range SKU, `amount` must be between `min_face_value` and `max_face_value`.
It is in `face_currency`.

Some range SKUs also have an `amount_step`. When it is not `null`, `amount` must be a multiple of it.
For example, with `"amount_step": "1"` you can send `25` but not `25.50`.
A quote or order with an amount that does not fit the step returns HTTP 400 and charges nothing.

### Direct top-ups

Some products top up your customer's account directly, for example a game account.
For these, CardV needs the account details. The SKU lists them:

```json
"required_input_schema": [
  {"key": "player_id", "label": "Player ID", "required": true},
  {"key": "server", "label": "Server", "required": false}
]
```

Send the values in the order line's `inputs`, using each `key`:

```json
"inputs": {"player_id": "123456789", "server": "EU"}
```

- A field is required unless it says `"required": false`.
- If a required value is missing, the order is rejected with an `items` error.
- These values are your customer's personal data. Protect them (see [Security](SECURITY.md)).

## Price quote

A quote tells you the current price for a quantity.

```http
GET /api/v1/skus/S000456/quote?quantity=2
GET /api/v1/skus/S000789/quote?quantity=1&amount=25.00
```

```json
{
  "sku_id": "S000456",
  "settlement_currency": "USD",
  "merchant_price": "9.25",
  "quantity": 2,
  "total_price": "18.50",
  "min_quantity": 1,
  "max_quantity": 100,
  "availability": "available"
}
```

- A quote does **not** hold the price. Prices can change at any time.
- To protect yourself, send `merchant_price` as `expected_unit_price` when you order.
  If the price changed, CardV rejects the order and charges nothing.
- A quantity or amount out of range, or an amount that is not a multiple of `amount_step`,
  returns HTTP 400 with a `quantity` or `amount` error.

## Place an order

`POST /api/v1/orders` buys one or more SKUs and pays from your wallet.
Like every call, it must be [signed](AUTHENTICATION.md#signing-a-request).

```json
{
  "external_order_id": "SHOP-20260929-10001",
  "items": [
    {"sku_id": "S000456", "quantity": 2, "expected_unit_price": "9.25"},
    {"sku_id": "S000789", "amount": "25.00", "expected_unit_price": "23.75"},
    {
      "sku_id": "S000900",
      "expected_unit_price": "4.90",
      "inputs": {"player_id": "123456789"}
    }
  ]
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `external_order_id` | Yes | Your order number, 1–120 characters. Must be unique. |
| `items` | Yes | One or more order lines. |
| `items[].sku_id` | Yes | The SKU to buy. |
| `items[].quantity` | No | How many. Default 1. |
| `items[].amount` | Range SKUs | The face value to buy. Must fit `min_face_value`, `max_face_value` and `amount_step`. |
| `items[].expected_unit_price` | Recommended | The quoted `merchant_price`. Always send it. |
| `items[].inputs` | Direct top-ups | Account details for [direct top-ups](#direct-top-ups). |

When CardV accepts the order, it charges the **full total** to your wallet at once.
Delivery then starts in the background.

The response is HTTP **201**:

```json
{
  "idempotent_replay": false,
  "order": {
    "order_id": "O-00001234",
    "external_order_id": "SHOP-20260929-10001",
    "status": "accepted",
    "total_amount": "46.20",
    "...": "more fields"
  }
}
```

Save `order.order_id`. This response never includes codes. Read them later ([Read an order](#read-an-order)).

### Rejected orders

A rejected order returns HTTP 400 and charges nothing. The error key tells you why:

| Key | Cause | What to do |
| --- | --- | --- |
| `items` | Price changed, SKU unavailable, bad amount or missing input | Get a new quote, fix it, send again |
| `balance` | Not enough money in your wallet | Add funds in the Portal |
| `risk` | Over your order size or daily limit | Contact CardV |
| `external_order_id` | Your order number was already used for a different order | See [Retry safely](#retry-safely) |

Example of a price change:

```json
{
  "items": "SKU S000456 price changed from 9.25 to 9.41 USD; refresh quote and confirm again."
}
```

Your account has limits on one order, on daily spend and on daily order count.
`GET /api/v1/account` shows them in `purchase_limits`, with what you have used today.
`0` means no limit. Daily limits reset at 00:00 UTC.

## Retry safely

Your order number (`external_order_id`) protects you from buying twice.
If you send the same order again with the same order number, CardV does **not** charge you again.
It returns the order it already has.

| You send | You get |
| --- | --- |
| A new order number | HTTP 201. A new order. Your wallet is charged. |
| The same order number and the same order | HTTP 200 and `"idempotent_replay": true`. The existing order. No charge. |
| The same order number but a different order | HTTP 400 on `external_order_id`. Nothing happens. |

"The same order" means the same lines, in the same sequence, with the same SKU, quantity, amount and inputs.
If you send `expected_unit_price`, it must match the price of the first order.

A repeated order is recognised before balance and price checks.
So it always returns the first order, even if the price has changed since.

### Safe retry flow

If you do not get a clear answer, just send the same order again.

```text
POST /orders with order number R
 ├─ 201 or 200 → save order_id. Done.
 ├─ 400 items / balance / risk → no order was made.
 │      Fix the cause and send again. You may reuse R.
 ├─ 400 external_order_id → R belongs to a different order. Stop and check.
 ├─ 403 signature error → sign again and send the same body.
 ├─ 429 → wait for Retry-After, sign again, send the same body.
 └─ timeout, 5xx or lost connection
        → send the same body again with the same R.
          You get 201 (the first try did not arrive) or 200 (it did).
```

Rules:

- **Never make a new order number because a response was lost.**
  If the first request did arrive, a new number would buy everything twice.
- Every resend needs a new timestamp, nonce and signature. The body stays the same.

## Read an order

`GET /api/v1/orders/{order_id}` returns the order, its status and its codes.

```json
{
  "order_id": "O-00001234",
  "external_order_id": "SHOP-20260929-10001",
  "status": "succeeded",
  "currency": "USD",
  "total_amount": "18.50",
  "created_at": "2026-09-29T08:15:30.123456Z",
  "updated_at": "2026-09-29T08:15:41.004211Z",
  "items": [
    {
      "sku_id": "S000456",
      "product_name": "Steam Wallet US",
      "quantity": 2,
      "unit_price": "9.25",
      "total_price": "18.50",
      "delivery_count": 2,
      "deliveries": [{"...": "see Codes below"}]
    }
  ],
  "...": "more fields"
}
```

- `total_amount` is what you were charged when the order was accepted.
- `items[].unit_price` is the price locked for this order.
- `items[].deliveries` holds the **full codes**. Treat the response as secret.
- `invoice_url` and `delivery_file_url` are paths to the invoice and to the codes as CSV.
  Both are Portal only. With an API key they return HTTP 403.
- Also returned: `id` (an old number, do not use it), `events` (a history for display only),
  and per-line delivery progress. You can ignore these.
- An unknown order ID returns HTTP 404.

## Order status and codes

### Status

```text
accepted ──► processing ──► succeeded
                  │
                  ├──► partially_succeeded   (some lines delivered, some not)
                  │
                  └──► failed ──► refunded   (money returned to your wallet)
```

| Status | Finished? | What to do |
| --- | --- | --- |
| `accepted` | No | Wait. The wallet is charged, delivery has not started. |
| `processing` | No | Wait. **Do not place the order again.** |
| `succeeded` | Yes | Read the codes and give them to your customer. |
| `partially_succeeded` | Yes | Deliver what arrived. The rest is refunded later. |
| `failed` | Not yet | Wait for `refunded`. Failed is not yet a refund. |
| `refunded` | Yes | The money is back in your wallet. |

If you do not use webhooks, poll like this: after 5 seconds, then 10 s, 30 s, 60 s,
then every 5 minutes. Stay within the [rate limit](CONVENTIONS.md#rate-limit).
Most orders finish in seconds. Some need a manual check and can take hours.

### Codes

Each delivered unit is one object in `items[].deliveries`:

```json
{
  "status": "stored",
  "delivery_type": "card_pin",
  "card_number": "X1234",
  "pin_code": "9876",
  "redeem_url": "",
  "expiry_date": "2027-09-29",
  "instructions": "Redeem at ..."
}
```

| Field | What it is |
|---|---|
| `card_number` | The main code: card number, voucher code or PIN. |
| `pin_code` | The second code, such as a PIN or security code. Empty when there is none. |
| `redeem_url` | Redemption link. For `link` deliveries the link itself is the code. |

- **Give your customer every field that is not empty**: `card_number`, `pin_code`,
  `redeem_url`, `expiry_date` and `instructions`.
- `delivery_type` says what you got: `code`, `card_pin`, `link`, `code_link` or `qr`.
- Keep `redeem_url` secret, like a code.
- Never give your customer a unit whose `status` is `voided`.
- Direct top-up products usually have no deliveries. `succeeded` means the account was topped up.
- Webhooks never contain codes. Read the order after a webhook arrives.
