// CardV Merchant API client (Node.js 18+, no dependencies).
// Signs every call with X-Key-Id + X-Timestamp + X-Nonce + X-Signature.
// Docs: https://cardv.net/developers/authentication/
//
// Usage:
//   CARDV_KEY_ID=ck_test_... CARDV_SIGNING_SECRET=cs_test_... \
//   CARDV_BASE_URL=https://sandbox.cardv.net node cardv-client.mjs
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

export function sign(secret, method, path, body, timestamp, nonce) {
  const bodyHash = crypto.createHash("sha256").update(body).digest("hex");
  const text = [method.toUpperCase(), path, timestamp, nonce, bodyHash].join("\n");
  return crypto.createHmac("sha256", secret).update(text, "utf8").digest("hex");
}

// Set userAgent to your app name and version; a clear User-Agent avoids edge blocks (error code 1010).
export function createClient({ baseUrl = "https://sandbox.cardv.net", keyId, signingSecret, userAgent = "CardV-Sample-Client/1.0 (node)" }) {
  const headers = (method, path, body) => {
    const timestamp = String(Math.floor(Date.now() / 1000));
    const nonce = crypto.randomBytes(16).toString("hex");
    return { "X-Key-Id": keyId, "X-Timestamp": timestamp, "X-Nonce": nonce, "X-Signature": sign(signingSecret, method, path, body, timestamp, nonce), "User-Agent": userAgent };
  };
  return {
    // Keep the query string inside `path`, so the signed path equals the sent path.
    async get(path) {
      const res = await fetch(baseUrl + path, { headers: headers("GET", path, Buffer.alloc(0)) });
      return { status: res.status, body: await res.json() };
    },
    async post(path, payload) {
      const body = Buffer.from(JSON.stringify(payload), "utf8"); // serialize once
      const res = await fetch(baseUrl + path, { method: "POST", headers: { ...headers("POST", path, body), "Content-Type": "application/json" }, body });
      return { status: res.status, body: await res.json() };
    },
  };
}

// Checks the signing code against the published test vectors (fake secret).
export function selfTest() {
  const secret = "cs_test_TEST_ONLY_not_a_real_secret_0123456789abcdef";
  const ts = "1790000000";
  const nonce = "0123456789abcdef0123456789abcdef";
  const get = sign(secret, "GET", "/api/v1/skus?limit=50", Buffer.alloc(0), ts, nonce);
  const body = Buffer.from('{"external_order_id":"TEST-0001","items":[{"sku_id":"S000001","quantity":1,"expected_unit_price":"9.2500"}]}');
  const post = sign(secret, "POST", "/api/v1/orders", body, ts, nonce);
  if (get !== "58f0362c355a6624fff9f0b84d47591c570263908832294375b7bf27731628e5") throw new Error("GET test vector failed");
  if (post !== "604b31bd10000c85a0e87e3b1e9d42225d7e8213f470b33f206f849ef99f8fcb") throw new Error("POST test vector failed");
  console.log("self-test passed");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  selfTest();
  const { CARDV_KEY_ID, CARDV_SIGNING_SECRET, CARDV_BASE_URL } = process.env;
  if (CARDV_KEY_ID && CARDV_SIGNING_SECRET) {
    const client = createClient({ baseUrl: CARDV_BASE_URL, keyId: CARDV_KEY_ID, signingSecret: CARDV_SIGNING_SECRET });
    console.log(await client.get("/api/v1/balance"));
  }
}
