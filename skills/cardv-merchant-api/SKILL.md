---
name: cardv-merchant-api
description: Build, debug or review an integration with the CardV Merchant API (b2b.cardv.net / sandbox.cardv.net), which sells gift cards, game top-ups, eSIM and mobile recharge to businesses from a prepaid wallet. Use when writing code that signs CardV requests, lists SKUs, quotes, places or retries orders, reads delivered codes, verifies CardV webhooks, runs mobile recharge, or when a CardV call returns 403, 400 or 429.
---

# CardV Merchant API

CardV is a B2B supplier of prepaid digital goods. A merchant's server buys them through this API and pays from a prepaid CardV wallet. Money, codes and customers' data move through this integration, so the safety rules below come first.

## Safety rules (always apply)

1. **Default to Sandbox.** Use `https://sandbox.cardv.net` unless the user explicitly says Live. Sandbox keys start with `ck_test_` / `cs_test_`, Live keys with `ck_live_` / `cs_live_`; a key never works in the other environment. In application code, read the base URL from config and require an explicit setting (for example `CARDV_ENV=live`) to switch to Live.
2. **A Live order spends real money.** When you (the agent) are about to send `POST /api/v1/orders` or `POST /api/v1/recharge/orders` to `https://b2b.cardv.net`, show the human the SKU or phone number, quantity or amount, and total price, and wait for an explicit yes. Never loop or batch Live orders without that confirmation. Code you write for the merchant's own checkout may order automatically; that is the merchant's business flow.
3. **Secrets come from the environment or a secret store**, never from code, config committed to git, URLs, logs, tickets or chat. Use `CARDV_KEY_ID`, `CARDV_SIGNING_SECRET`, `CARDV_WEBHOOK_SECRET`. If the user pastes a secret into the conversation, tell them to rotate it in the Portal.
4. **Never log or print** signing secrets, `X-Signature` / `X-CardV-Signature` headers, order responses with codes, `redeem_url`, or customer `inputs`. Log `order_id`, `external_order_id`, `sku_id` and the HTTP status instead.
5. **Treat codes as cash.** Store them encrypted; a `redeem_url` is itself a code. Sandbox codes cannot be redeemed, but handle them exactly like Live codes so the same code path is tested.

## Environments

| | Live | Sandbox |
| --- | --- | --- |
| API base | `https://b2b.cardv.net/api/v1` | `https://sandbox.cardv.net/api/v1` |
| Portal | `https://b2b.cardv.net/portal/` | same Portal, switch to **Sandbox** |

Keys, wallets, orders, SKU IDs and webhooks are separate per environment. Never copy Sandbox SKU IDs into Live config. Sandbox starts with 1,000 USD of test money.

Only these 13 endpoints accept an API key; everything else (funding, webhooks setup, API keys, IP allowlist, invoices, CSV exports) is Portal only and returns 403:

`GET /account` · `GET /balance` · `GET /skus` · `GET /skus/{sku_id}` · `GET /skus/{sku_id}/quote` · `POST /orders` · `GET /orders/{order_id}` · `GET /recharge/countries` · `GET /recharge/operators` · `POST /recharge/quote` · `POST /recharge/orders` · `GET /recharge/orders` · `GET /recharge/orders/{order_id}`

## Signing every request

Every call, including `GET`, sends `X-Key-Id`, `X-Timestamp` (Unix seconds, within 300 s), `X-Nonce` (32 random hex chars, never reused) and `X-Signature`:

```text
X-Signature = lowercase hex HMAC-SHA256(signing secret,
  METHOD + "\n" + PATH_WITH_QUERY + "\n" + X-Timestamp + "\n" + X-Nonce + "\n" + sha256_hex(body_bytes))
```

- Serialize the JSON body to bytes **once**; sign those bytes and send exactly those bytes. `{"a":1}` and `{"a": 1}` differ.
- The path includes the query string exactly as sent (`/api/v1/skus?limit=50`), no trailing slash.
- `GET` has an empty body: hash `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Every retry gets a new timestamp, nonce and signature, with the same body.
- Check signing code against the test vectors in `references/AUTHENTICATION.md` before calling the API. `python scripts/cardv_client.py` runs them.

Auth failures are HTTP **403** (not 401) with `{"detail": ...}`; rate limit is **429** with `Retry-After`. Plain-text `error code: 1010` means the network edge blocked the client: set a clear `User-Agent`, do not change the signature.

## Buying flow

1. `GET /account`: confirm `api_access_enabled: true`; read `purchase_limits`.
2. `GET /balance`: spend only `available_balance`.
3. `GET /skus?search=...&region=...&limit=...&offset=...`: page until `offset >= count` (max `limit` 500). `search` matches SKU ID, name or brand; `region` is a country code such as `US`. Order only `availability: "available"`. Cache the list 5–15 minutes. Map your products to `sku_id` once (in config or a table) instead of matching names on every order. Sandbox has a small test catalog with different SKU IDs from Live.
4. `GET /skus/{sku_id}/quote?quantity=N` (range SKUs also `&amount=` in `face_currency`). A quote does not hold the price.
5. `POST /orders` (signed) with a unique `external_order_id` (1–120 chars, `A–Z a–z 0–9 - _ .`) and `expected_unit_price` = the quoted `merchant_price` on every line. Range SKUs send `amount`; direct top-ups send `inputs` per `required_input_schema`. `201` = new order, charged in full at once.
6. Read codes with `GET /orders/{order_id}` or after a webhook. Codes are in `items[].deliveries[]`: give the customer every non-empty field (`card_number`, `pin_code`, `redeem_url`, `expiry_date`, `instructions`); never deliver a unit with `status: "voided"`.

Money is a decimal string: prices and balances have 2 decimals (`"9.25"`), face values read like the card (`"10"`, `"12.50"`). Compare values as decimals, never as strings or floats; `"25"` and `"25.00"` are the same amount. Pay attention to `settlement_currency` (what you pay) vs `face_currency` (printed on the card).

## Retries and idempotency (most important)

`external_order_id` prevents double purchase:

- same number + same body → `200`, `"idempotent_replay": true`, same order, no charge;
- same number + different body → `400` on `external_order_id`, stop and investigate;
- `400` on `items` / `balance` / `risk` → nothing was charged; fix and resend (same number is fine).
- **After a timeout, 5xx or lost connection, resend the same body with the same `external_order_id`.** Never generate a new order number because a response was lost: that buys twice.
- Suggested policy: retry about 5 times with backoff (1, 2, 4, 8, 16 s); on 429 wait `Retry-After`. If the outcome is still unknown, mark the order "unknown", alert a human, and resend later with the same number: a resend is safe at any time and returns the existing order if one was created.

## Order status

`accepted` → `processing` → `succeeded` | `partially_succeeded` | `failed` → `refunded`.
`failed` is not yet a refund; wait for `refunded` (tell the customer the order is delayed, not refunded). For `partially_succeeded`, compare each line's `delivery_count` with its `quantity` to see how many units are missing; deliver what arrived. Treat unknown statuses as not finished. Without webhooks, poll after 5 s, 10 s, 30 s, 60 s, then every 5 minutes, within 60 requests/minute per account.

## Webhooks

Events: `order.succeeded`, `order.partially_succeeded`, `order.failed`, `order.refunded`. They never contain codes: re-read the order.

- Verify `X-CardV-Signature: t=<ts>,v2=<hex>` where `v2 = HMAC-SHA256(webhook secret, "<t>.<X-CardV-Delivery>.<X-CardV-Event>." + raw body bytes)`, on the **raw** bytes before JSON parsing, constant-time compare, reject if `t` is more than 300 s off. Reject a header without `v2`. `scripts/verify_webhook.py --self-test` checks the published vector.
- Match a webhook to your order by `order.external_order_id` (it can arrive before your `POST /orders` response). If the order is not saved yet, answer non-2xx so CardV retries. Only API orders send webhooks; Portal orders do not.
- Answer 2xx within 15 s after storing the event; do slow work afterwards. No redirects are followed. Up to 6 tries.
- Deduplicate on `order.order_id` + `event`; events can repeat and arrive out of order. Also run a job for unfinished orders older than a few minutes.

## Mobile recharge

Separate flow: `GET /recharge/countries` → `GET /recharge/operators?country=XX` → signed `POST /recharge/quote` (returns `quote_token`, valid 300 s) → signed `POST /recharge/orders` with the same fields, the `account` phone number and the token. Same idempotency rules; `external_order_id` is unique across gift card and recharge orders. A top-up to a wrong number cannot be reversed: validate the number against the operator first. Details: `references/MOBILE-RECHARGE.md`.

## Review checklist

Signed bytes = sent bytes · no trailing slash, query string signed · new nonce and timestamp per try · same `external_order_id` on retry · `expected_unit_price` sent · decimals, not floats · every non-empty code field delivered · webhook `v2` verified on raw bytes with `X-CardV-Delivery` and `X-CardV-Event` · no codes or secrets in logs · clear `User-Agent` set.

## Files in this skill

| Need | Read |
| --- | --- |
| Overview, quick start, endpoint list | `references/README.md` |
| Headers, signing, test vectors, key rotation, IP allowlist | `references/AUTHENTICATION.md` |
| SKUs, quotes, orders, retries, statuses, codes | `references/CATALOG-AND-ORDERS.md` |
| Money, IDs, paging, rate limit, error keys | `references/CONVENTIONS.md` |
| Webhook payload, signature, retries, duplicates | `references/WEBHOOKS.md` |
| Mobile recharge | `references/MOBILE-RECHARGE.md` |
| Sandbox, test and go-live checklists | `references/SANDBOX.md` |
| Protecting keys, codes and customer data | `references/SECURITY.md` |
| Machine-readable spec | `references/cardv-openapi.json`, `references/cardv.postman_collection.json` |
| Working clients (signing + self-test) | `scripts/cardv_client.py`, `scripts/cardv_client.php`, `scripts/cardv-client.mjs` |
| Webhook signature check | `scripts/verify_webhook.py` |

Before go-live, walk the user through the checklists in `references/SANDBOX.md`. Support: `service@cardv.net` (never send secrets or codes). Full docs: https://cardv.net/developers/
