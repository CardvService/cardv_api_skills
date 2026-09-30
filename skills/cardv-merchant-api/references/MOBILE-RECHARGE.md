# Mobile recharge

Mobile recharge tops up a prepaid phone number directly.
Your customer gets airtime or data on their line. There is no code to hand over.
You pay from your CardV wallet, the same as for other orders.

Related: [Authentication](AUTHENTICATION.md) · [Conventions](CONVENTIONS.md) · [Webhooks](WEBHOOKS.md)

## How it works

```text
GET  /recharge/countries            which countries you can top up
GET  /recharge/operators?country=US  operators, recharge types and amounts
POST /recharge/quote                your price, and a quote_token valid for 300 s
POST /recharge/orders               place the order, paid from your wallet
GET  /recharge/orders/{order_id}    poll the status, or wait for a webhook
```

- All paths start with `/api/v1`. Send the same headers as on every call.
- Every call must be [signed](AUTHENTICATION.md#signing-a-request), including the `GET` calls.
  Sign them the same way as `POST /orders`, but use their own path,
  for example `/api/v1/recharge/quote`.
- Recharge orders are separate from gift card orders. Use the `/recharge` endpoints to read them.
- Only direct top-ups are offered. PIN products (a code the customer types in) are not.

## Countries

`GET /api/v1/recharge/countries` lists the countries you can top up now.

```json
{
  "count": 2,
  "results": [
    {"code": "MX", "name": "Mexico", "currency_codes": ["MXN"], "operator_count": 4, "offer_count": 37},
    {"code": "US", "name": "United States", "currency_codes": ["USD"], "operator_count": 6, "offer_count": 52}
  ]
}
```

- `code` is the ISO 3166-1 alpha-2 country code. Send it as `country` in later calls.
- `currency_codes` are the local currencies the operators in this country sell in.
- The list changes when operators are added or become unavailable. Load it every few hours.

## Operators

`GET /api/v1/recharge/operators?country=US` lists the operators in one country.
Add `search=att` to filter by operator name.

```json
{
  "count": 1,
  "results": [
    {
      "operator_key": "us-att",
      "name": "AT&T",
      "country": "US",
      "country_name": "United States",
      "logo_url": "https://b2b.cardv.net/api/v1/catalog-assets/3f5c...a1.png",
      "subtypes": ["airtime", "data"],
      "amount_model": "range",
      "currency_codes": ["USD"],
      "amounts": [
        {"min": "5.0000", "max": "100.0000", "currency": "USD", "subtype": "airtime", "label": "5.0000-100.0000 USD"},
        {"min": "15.0000", "max": "15.0000", "currency": "USD", "subtype": "data", "label": "15.0000 USD"}
      ],
      "offer_count": 3
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `operator_key` | The ID you send to quote and order, for example `us-att`. Store it as text. |
| `subtypes` | What you can buy: `airtime` (call credit), `data` or `bundle` (calls and data). |
| `amount_model` | `fixed` if every amount is a set value, `range` if any amount is a range. |
| `amounts[]` | Each option. If `min` equals `max`, it is a fixed amount. Otherwise any amount in between. |
| `amounts[].currency` | The local currency of that option. Send it as `local_currency`. |
| `logo_url` | Image hosted by CardV, or `""`. |

- Amounts are local amounts: what the phone line receives, in the local currency.
- An unknown or badly formed `country` returns HTTP 400.

## Quote

`POST /api/v1/recharge/quote` gives your price for one recharge. This call must be signed.

```json
{
  "country": "US",
  "operator_key": "us-att",
  "amount": "10.00",
  "local_currency": "USD",
  "subtype": "airtime"
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `country` | Yes | Country code from the countries list. |
| `operator_key` | Yes | From the operators list. |
| `amount` | Yes | Local amount, as a string. Fixed: one of the listed values. Range: between `min` and `max`. |
| `local_currency` | Recommended | ISO 4217 code of `amount`, from `amounts[].currency`. Send it when an operator lists more than one currency. |
| `subtype` | No | `airtime` (default), `data` or `bundle`. |

The response:

```json
{
  "country": "US",
  "country_name": "United States",
  "operator": {"operator_key": "us-att", "name": "AT&T", "logo_url": ""},
  "subtype": "airtime",
  "local_amount": "10.0000",
  "local_currency": "USD",
  "merchant_price": "9.6200",
  "merchant_currency": "USD",
  "expires_at": "2026-09-30T08:20:30.123456+00:00",
  "quote_token": "eyJ2ZXJzaW9uIjox...:1uXyZa:8c1f..."
}
```

- `merchant_price` is what your wallet pays, in `merchant_currency`.
- `quote_token` fixes this price for **300 seconds**, until `expires_at`. Send it unchanged with the order.
- The token is tied to your account and to this country, operator, type and amount.
- Check that `local_currency` is the currency you expected before you order.
- A quote does not reserve money. You can ask for a new quote at any time.

## Place a recharge order

`POST /api/v1/recharge/orders` tops up the phone and pays from your wallet. This call must be signed.

```json
{
  "external_order_id": "SHOP-RC-20260930-0001",
  "country": "US",
  "operator_key": "us-att",
  "amount": "10.00",
  "local_currency": "USD",
  "subtype": "airtime",
  "account": "12125550100",
  "quote_token": "eyJ2ZXJzaW9uIjox...:1uXyZa:8c1f..."
}
```

| Field | Required | Meaning |
| --- | --- | --- |
| `external_order_id` | Yes | Your order number. Unique across all your orders, including gift card orders. |
| `country`, `operator_key`, `amount`, `local_currency`, `subtype` | Yes | The same values you sent to the quote. |
| `account` | Yes | The phone number to top up. Send it with the country code (`12125550100`); `+1 212-555-0100` and a national number (`2125550100`) are also accepted. CardV stores it in international format, so all three are the same recipient. An invalid number returns HTTP 400 and charges nothing. |
| `quote_token` | Yes | From the quote, before it expires. |

Phone number examples: `12125550100` (United States), `525512345678` (Mexico).
Check that the number belongs to the chosen operator. A top-up sent to a wrong number cannot be reversed.

CardV checks the quote, charges `merchant_price` to your wallet at once, and starts the top-up in the background.
A new order returns HTTP **201**:

```json
{
  "idempotent_replay": false,
  "order": {
    "order_id": "O-00005678",
    "external_order_id": "SHOP-RC-20260930-0001",
    "status": "accepted",
    "status_title": "Recharge accepted",
    "poll_after_seconds": 12,
    "account": "12***00",
    "local_amount": "10.0000",
    "local_currency": "USD",
    "merchant_price": "9.6200",
    "merchant_currency": "USD",
    "...": "more fields"
  }
}
```

- Save `order.order_id`.
- The phone number is returned masked, never in full.

### Retry safely

`external_order_id` protects you from topping up twice.

| You send | You get |
| --- | --- |
| A new order number | HTTP 201. A new order. Your wallet is charged. |
| The same order number and the same recharge | HTTP 200 and `"idempotent_replay": true`. The existing order. No charge. |
| The same order number but a different recharge | HTTP 400 on `external_order_id`. Nothing happens. |

"The same recharge" means the same country, operator, type, amount and phone number.
A repeat is recognised before the quote is checked, so an expired `quote_token` still returns the first order.

- After a timeout, a 5xx or a lost connection, send the **same body** with the same order number.
  Sign it again with a new timestamp and nonce.
- **Never use a new order number because a response was lost.** That can top up the phone twice.

## Read recharge orders

`GET /api/v1/recharge/orders/{order_id}` returns one order.
You can use the CardV order ID (`O-00005678`).

```json
{
  "order_id": "O-00005678",
  "external_order_id": "SHOP-RC-20260930-0001",
  "status": "processing",
  "order_status": "processing",
  "status_title": "Recharge processing",
  "status_message": "The recharge request is being processed. Delivery is not confirmed yet.",
  "next_step": "Keep this order open and wait for confirmation before placing another recharge.",
  "poll_after_seconds": 12,
  "country": "US",
  "operator": {"operator_key": "us-att", "name": "AT&T", "logo_url": ""},
  "subtype": "airtime",
  "account": "12***00",
  "local_amount": "10.0000",
  "local_currency": "USD",
  "merchant_price": "9.6200",
  "merchant_currency": "USD",
  "attempts": [{"attempt_no": 1, "status": "processing", "error_message": "", "submitted_at": "2026-09-30T08:16:02.511201Z", "completed_at": null}],
  "created_at": "2026-09-30T08:16:01.004211Z",
  "updated_at": "2026-09-30T08:16:02.611978Z",
  "...": "more fields"
}
```

- An unknown order ID, or an order of another account, returns HTTP 404.
- `status_title`, `status_message` and `next_step` are English text you can show your staff.
- `poll_after_seconds` is how long to wait before the next check. `0` means the order is finished.

### List recharge orders

`GET /api/v1/recharge/orders` lists your recharge orders, newest first.

```http
GET /api/v1/recharge/orders?status=processing&limit=50&offset=0
```

```json
{"count": 3, "limit": 50, "results": ["..."]}
```

- Filters: `status`, and `search` (CardV order ID, your order number or operator name).
- `limit` defaults to 20. The maximum is 100. Larger values are reduced to 100.
- A negative or non-number `limit` or `offset` returns HTTP 400.

## Status

```text
accepted ──► processing ──► succeeded
                  │
                  ├──► manual_review ──► succeeded or refunded
                  │
                  └──► failed ──► refunded   (money returned to your wallet)
```

| Status | Finished? | What to do |
| --- | --- | --- |
| `accepted` | No | Wait. The wallet is charged, the top-up has not started. |
| `processing` | No | Wait. It can take several minutes. **Do not order again.** |
| `manual_review` | No | CardV is checking the result with the operator. Wait. |
| `succeeded` | Yes | The phone was topped up. Tell your customer. |
| `failed` | Not yet | The top-up did not go through. Wait for `refunded`. |
| `refunded` | Yes | The money is back in your wallet. You may place a new order. |

- Poll after `poll_after_seconds`, then back off: 30 s, 60 s, then every 5 minutes.
  Stay within the [rate limit](CONVENTIONS.md#rate-limit).
- Treat an unknown status as "not finished yet".
- While an order is not finished, do not send another recharge to the same number
  with a new order number. If the first one also succeeds, the phone is topped up twice.

## Webhooks and refunds

Recharge orders send the same [webhooks](WEBHOOKS.md) as other orders:
`order.succeeded`, `order.failed` and `order.refunded`.
The webhook has the CardV order ID and your order number, an empty `items` list, and an
`order.recharge` object: `type` (`mobile_recharge`), `status`, `country`, `country_name`,
`operator_key`, `operator_name`, `subtype`, `local_amount`, `local_currency` and the masked
`account_hint`. When a recharge fails you receive `order.failed` first, then `order.refunded`
once the debit is returned.
After a webhook, read the order with `GET /api/v1/recharge/orders/{order_id}`.

Refunds are automatic. When the operator confirms a failure, CardV returns the full
`merchant_price` to your wallet and the order becomes `refunded`.
You can see the refund in the Portal's transactions page.
A top-up that succeeded cannot be refunded or cancelled.

## Errors

Errors follow the [Conventions](CONVENTIONS.md#errors). A rejected quote or order returns HTTP 400 and charges nothing.

| Key | Where | What to do |
| --- | --- | --- |
| `detail` | Quote, order | Country, operator, type or amount not available. Check the operators list. |
| `amount` | Quote, order | Not a number, zero, or out of range. |
| `local_currency` | Quote, order | Not a 3-letter ISO 4217 code. |
| `account` | Order | Phone number missing, invalid, or not a number of the selected country. |
| `quote_token` | Order | Missing, expired, changed or not matching. See `code`, then quote again. |
| `balance` | Order | Add funds in the Portal. |
| `risk` | Order | You hit an order limit. Contact CardV. |
| `external_order_id` | Order | Used for a different order. See [Retry safely](#retry-safely). |
| `wallet` | Order | No active wallet. Contact CardV. |

`quote_token` errors come with a `code`:

```json
{"code": "quote_expired", "quote_token": "This quote expired. Refresh the price and confirm again."}
```

| `code` | Meaning |
| --- | --- |
| `quote_required` | No `quote_token` was sent. |
| `quote_expired` | Older than 300 seconds. Quote again. |
| `quote_invalid` | Changed, or for a different recharge. Quote again. |
| `price_changed` | Your price changed since the quote. Quote again and confirm the new price. |

HTTP 403 means a credentials, signature, IP or approval problem. See [Authentication](AUTHENTICATION.md#errors).
