# CardV Merchant API

CardV sells prepaid digital goods, such as gift cards, game top-ups and eSIM, to businesses.
The Merchant API lets your server buy them automatically.
You check your balance, find a product, get its price, place an order, and read back the codes.
Orders are paid from your prepaid CardV wallet.
Everything else, such as adding funds and viewing order history, is done in the Merchant Portal.

## Documentation

| Document | What it covers |
| --- | --- |
| [Authentication](AUTHENTICATION.md) | Headers, signing requests, key setup |
| [Catalog and orders](CATALOG-AND-ORDERS.md) | Balance, products, prices, orders, codes |
| [Mobile recharge](MOBILE-RECHARGE.md) | Phone top-ups: operators, quotes, recharge orders |
| [Conventions](CONVENTIONS.md) | Money, dates, IDs, rate limit, errors |
| [Webhooks](WEBHOOKS.md) | Order notifications sent to your server |
| [Sandbox](SANDBOX.md) | Testing, and the go-live checklist |
| [Security](SECURITY.md) | Protecting keys and codes |

## Environments

| | Live | Sandbox |
| --- | --- | --- |
| API base URL | `https://b2b.cardv.net/api/v1` | `https://sandbox.cardv.net/api/v1` |
| Merchant Portal | `https://b2b.cardv.net/portal/` | Same Portal, switch to **Sandbox** |

Sandbox is a separate test copy of CardV with test money.
Keys, balances, orders and product IDs are different in each environment.

## Quick start

1. **Apply** for a merchant account in the Portal and verify your email.
2. **Wait for approval.** CardV checks your business. You then get a Merchant ID, for example `M00000001`.
3. **Open Sandbox.** Sign in to the Portal and choose **Sandbox** in the header.
   You get 1,000 USD of test money.
4. **Create an API key.** In the Portal, go to Integrations → API keys.
   Create a key. The Portal shows the key ID and the signing secret once. Save the secret in your secret store.
5. **Check your balance:**

   ```bash
   export CARDV_BASE=https://sandbox.cardv.net
   export CARDV_KEY_ID=ck_test_...            # shown in the Portal
   export CARDV_SIGNING_SECRET=cs_test_...    # from your secret store

   cardv_get() {  # every call is signed, see Authentication
     local ts nonce sig
     ts=$(date +%s); nonce=$(openssl rand -hex 16)
     sig=$(printf 'GET\n%s\n%s\n%s\n%s' "$1" "$ts" "$nonce" \
       e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 \
       | openssl dgst -sha256 -hmac "$CARDV_SIGNING_SECRET" -hex | sed 's/^.*= //')
     curl -sS "$CARDV_BASE$1" -H "X-Key-Id: $CARDV_KEY_ID" \
       -H "X-Timestamp: $ts" -H "X-Nonce: $nonce" -H "X-Signature: $sig"
   }

   cardv_get "/api/v1/balance"
   ```

6. **Find a product:**

   ```bash
   cardv_get "/api/v1/skus?search=steam&limit=20"
   ```

   Pick one with `"availability": "available"` and note its `sku_id`.
7. **Get the price:**

   ```bash
   cardv_get "/api/v1/skus/S000001/quote?quantity=1"
   ```

   Note `merchant_price`. This is what you pay per unit.
8. **Place the order.** Sign it like every call.
   Use a sample from [Authentication](AUTHENTICATION.md#code-samples) with this body:

   ```json
   {
     "external_order_id": "TEST-0001",
     "items": [
       {"sku_id": "S000001", "quantity": 1, "expected_unit_price": "9.25"}
     ]
   }
   ```

   You get HTTP 201 with a CardV order ID such as `O-00001234`.
9. **Read the codes.** Call `GET /api/v1/orders/O-00001234` until the status is `succeeded`.
   The codes are in `items[].deliveries[]`: `card_number`, `pin_code` and `redeem_url`.
   You can also get a [webhook](WEBHOOKS.md) when the order finishes.
10. **Go live** after the [Sandbox checklist](SANDBOX.md#test-checklist).

The IDs and prices above are examples. Use the values your own catalog returns.

## The API at a glance

There are thirteen endpoints. Paths start with `/api/v1`.

| Endpoint | What it is for | Signed |
| --- | --- | --- |
| `GET /account` | Your company details and API status | No |
| `GET /balance` | How much money you can spend | No |
| `GET /skus` | List products you can buy, with your price | No |
| `GET /skus/{sku_id}` | One product | No |
| `GET /skus/{sku_id}/quote` | Current price for a quantity | No |
| `POST /orders` | Place an order, paid from your wallet | Yes |
| `GET /orders/{order_id}` | Order status and codes | No |
| `GET /recharge/countries` | Countries you can top up | No |
| `GET /recharge/operators` | Phone operators and amounts in a country | No |
| `POST /recharge/quote` | Price for one mobile recharge | Yes |
| `POST /recharge/orders` | Top up a phone, paid from your wallet | Yes |
| `GET /recharge/orders` | List your recharge orders | No |
| `GET /recharge/orders/{order_id}` | Recharge order status | No |

Any other endpoint returns HTTP 403 when called with an API key:

```json
{"detail": "This operation is only available in the Merchant Portal."}
```

Mobile recharge is explained in [Mobile recharge](MOBILE-RECHARGE.md).

### IDs

| Thing | Example | Notes |
| --- | --- | --- |
| Merchant ID | `M00000001` | Yours. Never changes. |
| SKU (a product you can buy) | `S000456` | Use it to quote and order. |
| CardV order ID | `O-00001234` | Save it with your order. |
| Your order number | `SHOP-10001` | You choose it (`external_order_id`). |

Store IDs as text. Do not parse them. See [Conventions](CONVENTIONS.md#identifiers).

## Done in the Merchant Portal

- Adding funds to your wallet, and the low-balance email alert
- Order history, search and CSV exports
- Order invoices
- Wallet transactions and reconciliation
- Webhook setup, delivery history and resending
- API keys
- IP allowlist
- Team members and roles
- Audit log
- Two-step verification (2FA)
- Switching between Live and Sandbox

## Compatibility and support

We may add new response fields and new status values without notice.
Ignore fields you do not know. Treat an unknown order status as "not finished yet".
Do not rely on the wording of error messages.

Email `service@cardv.net` with your Merchant ID, the environment, the order IDs, the time (UTC) and the HTTP status.
Never send API keys, signatures, webhook secrets or card codes.
