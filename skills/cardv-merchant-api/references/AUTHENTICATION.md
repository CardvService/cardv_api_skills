# Authentication

Every API call carries your key ID and a signature.
The signature proves the call comes from you, and nobody can change or repeat it.
Your signing secret itself is never sent.

Related: [Catalog and orders](CATALOG-AND-ORDERS.md) · [Security](SECURITY.md) · [README](README.md)

## Credentials

| Credential | Example | Secret? |
| --- | --- | --- |
| Key ID | `ck_live_...` | No. It says which key you use. |
| Signing secret | `cs_live_...` | **Yes.** You sign with it. It never leaves your server. |
| Merchant ID | `M00000001` | No. Optional on API calls. |

- An Owner creates keys in the Portal (see [API keys](#api-keys)).
- The Portal shows the signing secret **once**, when you create the key. Nobody can show it again, including CardV.
- Live keys start with `ck_live_` and `cs_live_`. Sandbox keys start with `ck_test_` and `cs_test_`.
  A key from one environment never works in the other.
- The API works only after CardV approves your business.
  `GET /account` then shows `"api_access_enabled": true`.

## Headers

Send these four headers on every call, including `GET` calls:

```http
X-Key-Id: ck_live_xxxxxxxxxxxxxxxxxxxxxxxx
X-Timestamp: 1790000000
X-Nonce: 0123456789abcdef0123456789abcdef
X-Signature: 604b31bd10000c85a0e87e3b1e9d42225d7e8213f470b33f206f849ef99f8fcb
```

- `X-Key-Id` is the public ID of your key.
- `X-Timestamp` is the current Unix time in seconds.
  It must be within 5 minutes (300 seconds) of CardV's clock.
- `X-Nonce` is a random value that you never use twice.
  Use 32 random hex characters.
- `X-Signature` is explained in [Signing a request](#signing-a-request). It must be lowercase hex.

You may also send `X-Merchant-Id`. If you do, it must match the key.

## Signing a request

1. Turn your request body into bytes **once**. You will sign and send these exact bytes.
   A `GET` call has an empty body.
2. Hash the body: `BODY_HASH` = SHA-256 of the body, as lowercase hex.
   For an empty body this is `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
3. Join these five lines with a newline (`\n`), with no newline at the end:

   ```text
   <METHOD>
   <PATH with query string>
   <X-Timestamp>
   <X-Nonce>
   <BODY_HASH>
   ```

   `METHOD` is upper case, for example `GET` or `POST`.
   The path includes the query string exactly as you send it, for example `/api/v1/skus?limit=50`.

4. Sign it: `X-Signature` = HMAC-SHA256 of that text, using your signing secret as the key.
   Write the result as lowercase hex.

The [mobile recharge](MOBILE-RECHARGE.md) calls are signed the same way, with their own path, for example `/api/v1/recharge/orders`.

The most common mistake is signing one version of the JSON and sending another.
For example, `{"a":1}` and `{"a": 1}` are different bytes.
Make sure your HTTP library does not change the body or reorder the query string after you sign it.

**Test vectors.** Check your code with these values. The secret is fake.

```text
Signing secret  cs_test_TEST_ONLY_not_a_real_secret_0123456789abcdef
X-Timestamp     1790000000
X-Nonce         0123456789abcdef0123456789abcdef
```

A `GET` call:

```text
Method       GET
Path         /api/v1/skus?limit=50
BODY_HASH    e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
X-Signature  58f0362c355a6624fff9f0b84d47591c570263908832294375b7bf27731628e5
```

A `POST` call to `/api/v1/orders` with this body (108 bytes, one line, no newline at the end):

```json
{"external_order_id":"TEST-0001","items":[{"sku_id":"S000001","quantity":1,"expected_unit_price":"9.2500"}]}
```

```text
BODY_HASH    b0545ae25d54b219f27d8bd90e4dcbf26cf0d491f53982da67b8eef0a1a59960
X-Signature  604b31bd10000c85a0e87e3b1e9d42225d7e8213f470b33f206f849ef99f8fcb
```

## Code samples

All samples produce the test vector results. Load the secret from your secret store, not from code.

**cURL (bash + OpenSSL)**

```bash
BASE_URL="https://sandbox.cardv.net"
REQ_PATH="/api/v1/orders"      # do not call this variable PATH
BODY='{"external_order_id":"SHOP-10001","items":'
BODY+='[{"sku_id":"S000001","quantity":1,"expected_unit_price":"9.2500"}]}'
TS=$(date +%s)
NONCE=$(openssl rand -hex 16)
BODY_HASH=$(printf '%s' "$BODY" | openssl dgst -sha256 -hex | sed 's/^.*= //')
SIG=$(printf 'POST\n%s\n%s\n%s\n%s' "$REQ_PATH" "$TS" "$NONCE" "$BODY_HASH" \
  | openssl dgst -sha256 -hmac "$CARDV_SIGNING_SECRET" -hex | sed 's/^.*= //')

curl -sS -X POST "$BASE_URL$REQ_PATH" \
  -H "Content-Type: application/json" \
  -H "X-Key-Id: $CARDV_KEY_ID" \
  -H "X-Timestamp: $TS" \
  -H "X-Nonce: $NONCE" \
  -H "X-Signature: $SIG" \
  --data-raw "$BODY"
```

Use `--data-raw`, not `-d @file`. `-d` removes newlines, so the sent bytes would not match.
For a `GET` call, sign `GET`, the path with its query string, and the empty-body hash, and send no body.

**Python (requests)**

```python
import hashlib, hmac, json, os, secrets, time
import requests

BASE_URL = "https://sandbox.cardv.net"
KEY_ID = os.environ["CARDV_KEY_ID"]
SIGNING_SECRET = os.environ["CARDV_SIGNING_SECRET"]


def signed_headers(method: str, path: str, body: bytes) -> dict:
    ts, nonce = str(int(time.time())), secrets.token_hex(16)
    body_hash = hashlib.sha256(body).hexdigest()
    text = "\n".join([method, path, ts, nonce, body_hash])
    signature = hmac.new(SIGNING_SECRET.encode(), text.encode(), hashlib.sha256).hexdigest()
    return {"X-Key-Id": KEY_ID, "X-Timestamp": ts, "X-Nonce": nonce, "X-Signature": signature}


def cardv_get(path: str) -> requests.Response:
    # Put the query string in `path` so the signed path and the sent path are identical.
    return requests.get(BASE_URL + path, headers=signed_headers("GET", path, b""), timeout=30)


def cardv_post(path: str, payload: dict) -> requests.Response:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    headers = {**signed_headers("POST", path, body), "Content-Type": "application/json"}
    return requests.post(BASE_URL + path, data=body, headers=headers, timeout=30)


resp = cardv_post("/api/v1/orders", {
    "external_order_id": "SHOP-10001",
    "items": [{"sku_id": "S000001", "quantity": 1, "expected_unit_price": "9.2500"}],
})
print(resp.status_code, resp.json())

order_id = resp.json()["order"]["order_id"]
print(cardv_get(f"/api/v1/orders/{order_id}").json()["status"])
```

**Node.js 18+ (built-in fetch)**

```js
import crypto from "node:crypto";

const BASE_URL = "https://sandbox.cardv.net";
const { CARDV_KEY_ID, CARDV_SIGNING_SECRET } = process.env;

function signedHeaders(method, path, body) {
  const timestamp = String(Math.floor(Date.now() / 1000));
  const nonce = crypto.randomBytes(16).toString("hex");
  const bodyHash = crypto.createHash("sha256").update(body).digest("hex");
  const text = [method, path, timestamp, nonce, bodyHash].join("\n");
  const signature = crypto.createHmac("sha256", CARDV_SIGNING_SECRET).update(text, "utf8").digest("hex");
  return { "X-Key-Id": CARDV_KEY_ID, "X-Timestamp": timestamp, "X-Nonce": nonce, "X-Signature": signature };
}

async function cardvGet(path) {
  const res = await fetch(BASE_URL + path, { headers: signedHeaders("GET", path, Buffer.alloc(0)) });
  return { status: res.status, body: await res.json() };
}

async function cardvPost(path, payload) {
  const body = Buffer.from(JSON.stringify(payload), "utf8"); // serialize once
  const headers = { ...signedHeaders("POST", path, body), "Content-Type": "application/json" };
  const res = await fetch(BASE_URL + path, { method: "POST", headers, body });
  return { status: res.status, body: await res.json() };
}

console.log(await cardvPost("/api/v1/orders", {
  external_order_id: "SHOP-10001",
  items: [{ sku_id: "S000001", quantity: 1, expected_unit_price: "9.2500" }],
}));
console.log(await cardvGet("/api/v1/balance"));
```

**PHP (signing only)**

```php
<?php
function cardv_sign(
    string $secret, string $method, string $path, string $body, string $ts, string $nonce
): string {
    $text = implode("\n", [$method, $path, $ts, $nonce, hash('sha256', $body)]);
    return hash_hmac('sha256', $text, $secret); // lowercase hex
}

// Send exactly $body. For a GET call use $body = ''.
$body = json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
$ts = (string) time();
$nonce = bin2hex(random_bytes(16));
$signature = cardv_sign($signingSecret, 'POST', '/api/v1/orders', $body, $ts, $nonce);
// Headers: X-Key-Id, X-Timestamp, X-Nonce, X-Signature
```

## Errors

All of these return HTTP 403 (not 401), except the rate limit, which returns 429.
The body looks like this:

```json
{"detail": "Invalid HMAC signature."}
```

| Problem | What to do |
| --- | --- |
| Unknown or disabled key ID | Check `X-Key-Id` and the environment (Live or Sandbox). |
| API access not enabled | Wait for CardV to approve your business. |
| Your server's IP is not allowed | Add it to the IP allowlist in the Portal. |
| Endpoint is Portal only | Use the Portal. Only thirteen endpoints work with a key. |
| Missing or wrong signature | Fix your signing code. Test it with the test vectors. |
| Timestamp too old or new | Sync your server clock (NTP). |
| Nonce already used | Use a new random nonce on every request. |
| Too many requests (429) | Wait the seconds in `Retry-After`, then try again. |

Important:

- When you send a request again, create a **new** timestamp, nonce and signature.
  Keep the body the same. See [safe retries](CATALOG-AND-ORDERS.md#safe-retry-flow).
- A nonce is used up even if the signature was wrong.
- CardV records failed attempts and alerts its team if there are many.

## IP allowlist

The IP allowlist lets only your servers use your key. You manage it in the Portal (Owner).

- It is optional. With no rules, calls from any IP are accepted.
- With at least one rule, calls from other IPs get HTTP 403.
- Rules look like `203.0.113.10/32` (IPv4) or `2001:db8::/48` (IPv6).
- It applies only to API key calls, not to Portal sign-in.
- Add every server IP before you turn it on, including NAT gateways and backup regions.

## API keys

A key can use exactly the thirteen endpoints in
[The API at a glance](README.md#the-api-at-a-glance).
That includes placing orders and reading codes, so guard the signing secret like an Owner password.

Only an Owner can manage keys, in the Portal under Integrations → API keys.
Do this separately in Live and Sandbox.

1. **Create** a key and give it a name.
   The Portal shows the key ID and the signing secret. Copy the secret into your secret store now.
   It is shown only this once.
2. **Regenerate the secret** if you lose it. The key ID stays the same.
   The old secret stops working at once, so deploy the new one to all your servers right away.
3. **Disable** a key when you no longer need it. This is immediate and permanent.
   You can then remove the disabled key from the list. CardV keeps its history.

To change keys without downtime:

1. Create a new key and save its secret.
2. Deploy it to all your servers.
3. Check in the Portal that the old key is no longer used.
4. Disable the old key.

Change keys at least once a year, and whenever someone with access leaves.
If a key may have leaked, disable it first, then investigate.

## Legacy keys

Keys created before October 2026 start with `cvb2b_` and use the older headers
`X-Merchant-Id` and `X-Api-Key`, with a signature only on `POST` calls.
The older key travels with every request, so it is easier to leak.

Live and Sandbox no longer accept these keys.
Move to a new key now: create one in the Portal, switch your code to the headers above, then disable the old key.
