# Sandbox

Sandbox is a separate test copy of CardV. Use it to build and test your integration
without real money or real products.

Related: [README](README.md) · [Authentication](AUTHENTICATION.md)

| | Live | Sandbox |
| --- | --- | --- |
| API base URL | `https://b2b.cardv.net/api/v1` | `https://sandbox.cardv.net/api/v1` |
| Portal | `https://b2b.cardv.net/portal/` | Same Portal, switch to **Sandbox** |

## Getting access

1. Your business must be approved by CardV first.
2. Sign in to the Portal and choose **Sandbox** in the header.
   You cannot sign in to Sandbox directly.
3. The first time, CardV creates your Sandbox account.
   It has the same Merchant ID and **1,000 USD of test money**.
4. In Sandbox, an Owner creates a **Sandbox API key** (`ck_test_...`) and saves its signing secret. Live keys do not work here.
5. Optional: set up a Sandbox webhook. It has its own signing secret.

## What is separate

- Sandbox has its own keys, wallet, orders, webhooks, IP allowlist and audit log.
- Settings are not shared. Set up keys, webhooks and the IP allowlist in each environment.
- Sandbox orders never buy real products. Test codes cannot be redeemed.
- Test money has no value. You cannot add funds in Sandbox, withdraw, or move it to Live.
- If you run out of test money, ask CardV support for more.

### Test money

Orders use test money exactly as Live orders use real money.
Failed test orders are refunded in the same way.
You can see test money movements in the Portal's transactions page.

### Test catalog

- The Sandbox catalog is small and has test products only.
- **SKU IDs are different from Live.** Always find them with `GET /skus` in Sandbox.
- Never copy Sandbox IDs into your Live setup, or the other way round.
- Prices, availability and delivery speed in Sandbox are not the same as Live.
- Sandbox mobile recharge uses test operator data. Countries, operators and amounts differ from Live, and no real phone is topped up.

## Test checklist

- [ ] `GET /account` shows your Merchant ID and `"api_access_enabled": true`.
- [ ] `GET /balance` works.
- [ ] You can page through `GET /skus` and only order `available` SKUs.
- [ ] Signed `GET` calls and a signed order succeed. A wrong signature gets HTTP 403.
- [ ] You send `expected_unit_price` on every order line.
- [ ] A range SKU order with `amount` works (if Sandbox has one).
- [ ] **Sending the same order twice** (new nonce, same body and order number)
      returns HTTP 200 with the same `order_id`. Your balance is charged only once.
- [ ] The same order number with a different body returns HTTP 400 on `external_order_id`.
- [ ] After a timeout, your code resends the same order instead of making a new order number.
- [ ] You read `card_number`, `pin_code` and `redeem_url` from `deliveries[]` and give them to the customer.
- [ ] You handle `failed`, `refunded` and `partially_succeeded`.
- [ ] If you sell mobile recharge: you list operators, get a quote and place a signed recharge order
      within 300 seconds. You follow it to `succeeded` or `refunded`. Sending it again returns HTTP 200.
- [ ] Your webhook code passes the [test vector](WEBHOOKS.md#signature-check),
      then a real Sandbox webhook. Duplicates are ignored.
- [ ] You wait for `Retry-After` after HTTP 429.
- [ ] Your logs contain no signing secrets, signatures, codes or customer account details.

## Go-live checklist

- [ ] Create a **Live** API key in the Live Portal. Store its signing secret in your production secret store.
- [ ] Change the base URL to `https://b2b.cardv.net/api/v1` in configuration.
- [ ] Load the Live catalog and map your products to Live SKU IDs.
- [ ] Add funds to your Live wallet in the Portal. Set a low-balance alert.
- [ ] Optional: add your server IPs to the Live IP allowlist.
- [ ] Set up a Live webhook and deploy its signing secret.
- [ ] Confirm your order limits and rate limit with CardV.
- [ ] Place **one** small Live order. Check the charge, the codes and the webhook.
      Then increase traffic step by step.
- [ ] Reconcile daily using the transactions page and exports in the Portal.
- [ ] Turn on two-step verification for all Owners.

## Troubleshooting

**HTTP 403 `error code: 1010`**

The Sandbox host sits behind a network edge service. Some HTTP clients get HTTP 403
with the plain text `error code: 1010`. The request never reached CardV,
so changing your key or signature does not help.

- Set a clear `User-Agent`.
- If it continues, send CardV support your server IP, `User-Agent` and the time.
- Never test against Live instead.
