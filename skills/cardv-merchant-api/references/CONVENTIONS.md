# Conventions

Rules that apply to all thirteen endpoints.

Related: [Authentication](AUTHENTICATION.md) · [Catalog and orders](CATALOG-AND-ORDERS.md) · [README](README.md)

## Requests

- Base URL: `https://b2b.cardv.net/api/v1` (Live) or `https://sandbox.cardv.net/api/v1` (Sandbox).
- Paths have **no trailing slash**. Use `/api/v1/orders`, not `/api/v1/orders/`.
- Send JSON bodies as UTF-8 with `Content-Type: application/json`.
- Send amounts as strings, for example `"9.25"`. No padding is needed: `"25"`, `"25.5"` and `"25.50"` are the same amount. Up to 4 decimals are accepted.
- Set a clear `User-Agent`, for example `AcmeShop-CardV/1.4`.

## Money and time

- Prices, totals and balances have 2 decimals, for example `"merchant_price": "9.25"`. More decimals appear only when the amount really has them.
- Face values are written like the card, for example `"denomination_value": "10"` or `"12.50"`.
- Read it with a decimal type, never a floating-point number.
- You pay in your wallet currency (`default_currency` in `GET /account`, currently USD).
- `face_currency` is the currency printed on the card. It can differ from your wallet currency.
- Always use `merchant_price` for your costs. Labels such as `price_label` are for display only.
- All times are UTC in ISO 8601, for example `2026-09-29T08:15:30.123456Z`.
- Use a real ISO 8601 parser. The number of decimals in seconds can vary.
- `X-Timestamp` for signing is Unix time in seconds.

## Identifiers

| Thing | Example | Notes |
| --- | --- | --- |
| Merchant ID | `M00000001` | Never changes. |
| SKU ID | `S000456` | Use it to quote and order. |
| Product ID | `P000123` | The product a SKU belongs to. |
| CardV order ID | `O-00001234` | Use it to read an order. |
| Your order number | `SHOP-10001` | `external_order_id`, 1–120 characters, unique. |

- Store IDs as text. Do not parse them. They may get longer.
- Orders also have a numeric `id`. Do not use it. Use `order_id`.
- For your order number, use only `A–Z a–z 0–9 - _ .`.

## Paging

`GET /skus` is paged. Send `limit` and `offset`:

```http
GET /api/v1/skus?limit=100&offset=200
```

```json
{"count": 1234, "limit": 100, "results": ["..."], "filter_options": {}}
```

- `limit` defaults to 100. The maximum is 500. Larger values are reduced to 500.
- `count` is the total number of matches. Keep going until `offset` reaches `count`.
- A negative or non-number `limit` or `offset` returns HTTP 400.
- An unknown filter value returns an empty list, not an error.
- `GET /recharge/orders` is also paged, with smaller limits. See [Mobile recharge](MOBILE-RECHARGE.md#list-recharge-orders).

## Rate limit

- The default is **60 requests per minute** for your whole account.
  All your keys and Portal users share it. Your account may have a different number.
- The minute starts at `:00` on the clock. Rejected requests also count.
- Over the limit, you get HTTP 429 and a `Retry-After` header (seconds to wait):

  ```json
  {"detail": "Merchant API rate limit exceeded. Expected available in 23 seconds."}
  ```

- New orders have a separate, lower limit: by default **20 new orders per minute**.
  Gift card orders (`POST /orders`) and recharge orders (`POST /recharge/orders`) share it.
  Your account may have a different number. An order request counts toward both limits.
- Sending an `external_order_id` that already exists replays the original order.
  The replay does not use the order limit, so a safe retry is not blocked by it.
- Over the order limit, you also get HTTP 429 and `Retry-After`:

  ```json
  {"detail": "Merchant order rate limit exceeded. Expected available in 23 seconds."}
  ```

- To stay under it: cache the SKU list, use webhooks instead of fast polling,
  and wait a little longer after each 429.

## Errors

Always check the HTTP status first. Then read the JSON body.
The **key** in the body tells you what went wrong. Do not rely on the message text.

Authentication, permission, not-found and rate-limit errors use `detail`:

```json
{"detail": "Order not found."}
```

Order and quote errors name the field:

```json
{"balance": "Insufficient available balance."}
```

A badly formed order line is reported per line, in the same position as your `items`:

```json
{"items": [{}, {"quantity": ["Ensure this value is greater than or equal to 1."]}]}
```

| Key | Where | What to do |
| --- | --- | --- |
| `detail` | Any | See the status code below. |
| `items` | `POST /orders` | Fix the line. If the price changed, quote again. |
| `balance` | `POST /orders` | Add funds in the Portal. |
| `risk` | `POST /orders` | You hit an order limit. Contact CardV. |
| `external_order_id` | `POST /orders` | Order number missing, too long or used for another order. |
| `wallet` | `POST /orders` | No active wallet. Contact CardV. |
| `quantity`, `amount` | Quote | Out of range or not a number. |
| `limit`, `offset` | `GET /skus` | Not a valid number. |

A few errors are not JSON:

- HTTP 403 with plain text such as `error code: 1010` comes from CardV's network edge.
  Your request never reached CardV. Send CardV your server IP and `User-Agent`.
- An unknown path (404) or a proxy error (5xx) can return HTML.

Never log signing secrets, signatures or codes when you log errors.

### HTTP status codes

| Status | Meaning | Retry? |
| --- | --- | --- |
| 200 | Success. On `POST /orders`: the order already existed. | No need |
| 201 | A new order was created. | No need |
| 400 | The request was rejected. Nothing was charged. | After fixing it |
| 403 | Credentials, signature, IP, or a Portal-only endpoint. | After fixing it |
| 404 | Not found, or not open to your account. | No |
| 405 | Wrong method for this path. | No |
| 429 | Too many requests. | After `Retry-After` |
| 5xx or timeout | Server or network problem. The order may exist. | Yes, see below |

For `POST /orders`, retry only with the same body and order number.
See the [safe retry flow](CATALOG-AND-ORDERS.md#safe-retry-flow).

## Responses

- `brand_logo_url` and `image_url` are full URLs to images hosted by CardV, or `""`.
  They are public and can be cached.
- The order fields `invoice_url` and `delivery_file_url` are paths such as
  `/orders/O-00001234/invoice`, or `""` when there is nothing yet.
  They are Portal only: with an API key they return HTTP 403.
  Open invoices and code CSV files in the Portal.

### Compatibility

- Ignore fields you do not know. CardV adds fields without a new API version.
- New status values may appear. Treat an unknown status as "not finished yet".
- Do not depend on the order of JSON keys or the wording of messages.
