# Webhooks

A webhook is a message CardV sends to your server when an order finishes.
It saves you from polling. It never contains codes: after a webhook, read the order with
`GET /api/v1/orders/{order_id}`.

You set up webhook URLs in the Portal (Owner, Integrations → Webhooks),
separately for Live and Sandbox. There is no API for this.

Related: [Catalog and orders](CATALOG-AND-ORDERS.md) · [Security](SECURITY.md)

## Events

| Event | Sent when the order becomes |
| --- | --- |
| `order.succeeded` | `succeeded` |
| `order.partially_succeeded` | `partially_succeeded` |
| `order.failed` | `failed` (this is not yet a refund) |
| `order.refunded` | `refunded` (money is back in your wallet) |

- Each event is sent at most once per order and webhook URL (plus [retries](#retries)).
- There are no events for `accepted` or `processing`, or for adding funds.

## Payload

CardV sends a `POST` to your HTTPS URL:

```http
POST /cardv/webhook HTTP/1.1
Content-Type: application/json
User-Agent: CardV-B2B-Webhook/1.0
X-CardV-Event: order.succeeded
X-CardV-Delivery: 5521
X-CardV-Timestamp: 1790000100
X-CardV-Signature: t=1790000100,v1=2baac51da272ee8d4b7b1382d48037976c7272f1749c9399a50e758604de8a27
```

The body, shown formatted here (CardV sends it on one line):

```json
{
  "event": "order.succeeded",
  "order": {
    "id": "O-00000001",
    "order_id": "O-00000001",
    "external_order_id": "TEST-0001",
    "status": "succeeded",
    "currency": "USD",
    "total_amount": "9.2500",
    "items": [
      {
        "sku_id": "S000001",
        "product_name": "Example Card",
        "quantity": 1,
        "delivery_count": 1
      }
    ]
  }
}
```

- `order.order_id` is the CardV order ID. `order.id` holds the same value.
- `order.external_order_id` is your order number.
- `order.status` is the status **at the time of the event**. It may be out of date.
- `X-CardV-Delivery` is the ID of this message. The Portal shows it in the delivery history.

## Signature check

Every webhook is signed with your webhook's signing secret (`whsec_...`).
The Portal shows the secret **only once**, when you create the webhook or reset the secret.

How the signature works:

```text
X-CardV-Signature: t=<unix seconds>,v1=<lowercase hex>
v1 = HMAC-SHA256(key = signing secret, message = "<t>" + "." + raw body bytes)
```

Steps:

1. Read the **raw body bytes**, before you parse the JSON.
2. Take `t` and `v1` from the header.
3. Reject the message if `t` is more than 300 seconds from your clock.
4. Compute the expected `v1` and compare it with a constant-time compare.
5. Only then parse the JSON.

Only `t` and the body are signed. Take the event type from the body's `event` field,
not from the `X-CardV-Event` header.

**Test vector** (fake secret):

```text
secret   whsec_TEST_ONLY_not_a_real_secret_000000000000
t        1790000100
v1       2baac51da272ee8d4b7b1382d48037976c7272f1749c9399a50e758604de8a27
```

The body for this vector is exactly this one line (266 bytes, no newline at the end):

```json
{"event":"order.succeeded","order":{"id":"O-00000001","order_id":"O-00000001","external_order_id":"TEST-0001","status":"succeeded","currency":"USD","total_amount":"9.2500","items":[{"sku_id":"S000001","product_name":"Example Card","quantity":1,"delivery_count":1}]}}
```

**Python (Flask)**

```python
import hashlib, hmac, os, time
from flask import Flask, request, abort

app = Flask(__name__)
SECRET = os.environ["CARDV_WEBHOOK_SECRET"].encode()


def verify(raw_body: bytes, header: str, tolerance: int = 300) -> bool:
    try:
        parts = dict(item.split("=", 1) for item in header.split(","))
        t, v1 = parts["t"].strip(), parts["v1"].strip()
    except (KeyError, ValueError):
        return False
    if not t.isdigit() or abs(time.time() - int(t)) > tolerance:
        return False
    signed = t.encode() + b"." + raw_body
    expected = hmac.new(SECRET, signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.encode(), v1.encode())  # constant time


@app.post("/cardv/webhook")
def cardv_webhook():
    raw = request.get_data()  # raw bytes, before JSON parsing
    if not verify(raw, request.headers.get("X-CardV-Signature", "")):
        abort(400)
    event = request.get_json()
    store_event(request.headers["X-CardV-Delivery"], event)  # your code
    return "", 204  # answer fast; do the work later
```

**Node.js (Express)**

```js
import crypto from "node:crypto";
import express from "express";

const app = express();
const SECRET = process.env.CARDV_WEBHOOK_SECRET;

function verify(rawBody, header, toleranceSeconds = 300) {
  const parts = {};
  for (const p of String(header || "").split(",")) {
    const i = p.indexOf("=");
    parts[p.slice(0, i).trim()] = p.slice(i + 1).trim();
  }
  const { t, v1 } = parts;
  if (!t || !v1 || !/^\d+$/.test(t)) return false;
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - Number(t)) > toleranceSeconds) return false;
  const expected = crypto.createHmac("sha256", SECRET)
    .update(Buffer.concat([Buffer.from(`${t}.`, "utf8"), rawBody]))
    .digest("hex");
  const a = Buffer.from(expected, "utf8");
  const b = Buffer.from(v1, "utf8");
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

// express.raw keeps the exact bytes. Do not use express.json() on this route.
const rawJson = express.raw({ type: "application/json" });

app.post("/cardv/webhook", rawJson, async (req, res) => {
  if (!verify(req.body, req.get("X-CardV-Signature"))) return res.sendStatus(400);
  const event = JSON.parse(req.body.toString("utf8"));
  await storeEvent(req.get("X-CardV-Delivery"), event); // your code
  res.sendStatus(204);
});
```

Both samples pass the test vector.

## Retries

- Answer with any **2xx** status within **15 seconds**, after you have saved the event.
  Do the slow work (reading the order, sending codes) afterwards.
- Anything else counts as a failure: another status, a timeout, or a connection error.
- CardV does **not follow redirects**. A 3xx answer is a failure.
  Register the exact final URL.
- A failed message is retried, up to **6 tries in total**:

| Try | When |
| --- | --- |
| 1 | Right after the event |
| 2 | About 1 minute after try 1 failed |
| 3 | About 5 minutes after try 2 failed |
| 4 | About 15 minutes after try 3 failed |
| 5 | About 30 minutes after try 4 failed |
| 6 | About 60 minutes after try 5 failed |

Times can be up to a minute later. After the 6th failure, CardV stops trying.
You can see every message and send it again from the Portal's delivery history.

## Duplicates

The same event can arrive more than once, and events can arrive out of order.

- Ignore an event you have already handled.
  Match on `order.order_id` plus `event` from the verified body.
  A message resent from the Portal gets a new `X-CardV-Delivery` ID, so that ID alone is not enough.
- The body is a snapshot from when the event happened.
  Always read the order again and act on its **current** status.
- Webhooks can be missed. Also run a job that checks unfinished orders
  older than a few minutes.

## Endpoint rules

- The URL must start with `https://` and point to a public internet address.
  Private and local addresses are rejected.
  URLs on CardV's own domains and servers are also rejected.
- You can subscribe to all four events or pick some.
- Resetting the signing secret takes effect at once. The old secret stops working.
  To switch without downtime, add a second webhook with a new secret, deploy it,
  then disable the old one.
- CardV keeps the first 1,000 characters of your answer for troubleshooting.
  Do not put secrets or personal data in your answer.
