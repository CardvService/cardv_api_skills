"""CardV Merchant API client (Python 3.9+, requests).

Signs every call with X-Key-Id + X-Timestamp + X-Nonce + X-Signature.
Docs: https://cardv.net/developers/authentication/

Usage:
    export CARDV_KEY_ID=ck_test_...
    export CARDV_SIGNING_SECRET=cs_test_...
    export CARDV_BASE_URL=https://sandbox.cardv.net   # or https://b2b.cardv.net
    python cardv_client.py            # runs the self-test, then GET /api/v1/balance
"""
import hashlib
import hmac
import json
import os
import secrets
import time

USER_AGENT = "CardV-Sample-Client/1.0 (python)"  # replace with your app name and version


def sign(secret: str, method: str, path: str, body: bytes, timestamp: str, nonce: str) -> str:
    text = "\n".join([method.upper(), path, timestamp, nonce, hashlib.sha256(body).hexdigest()])
    return hmac.new(secret.encode(), text.encode(), hashlib.sha256).hexdigest()


class CardV:
    def __init__(self, base_url: str, key_id: str, signing_secret: str, timeout: int = 30):
        import requests  # imported here so the self-test runs without it

        self.session = requests.Session()
        self.base_url = base_url.rstrip("/")
        self.key_id = key_id
        self.secret = signing_secret
        self.timeout = timeout

    def _headers(self, method: str, path: str, body: bytes) -> dict:
        ts, nonce = str(int(time.time())), secrets.token_hex(16)
        return {
            "X-Key-Id": self.key_id,
            "X-Timestamp": ts,
            "X-Nonce": nonce,
            "X-Signature": sign(self.secret, method, path, body, ts, nonce),
            "User-Agent": USER_AGENT,  # a clear User-Agent avoids edge blocks (error code 1010)
        }

    def get(self, path: str):
        # Keep the query string inside `path`, so the signed path equals the sent path.
        return self.session.get(self.base_url + path, headers=self._headers("GET", path, b""), timeout=self.timeout)

    def post(self, path: str, payload: dict):
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()  # serialize once
        headers = {**self._headers("POST", path, body), "Content-Type": "application/json"}
        return self.session.post(self.base_url + path, data=body, headers=headers, timeout=self.timeout)


def self_test() -> None:
    """Checks the signing code against the published test vectors (fake secret)."""
    secret = "cs_test_TEST_ONLY_not_a_real_secret_0123456789abcdef"
    ts, nonce = "1790000000", "0123456789abcdef0123456789abcdef"
    assert sign(secret, "GET", "/api/v1/skus?limit=50", b"", ts, nonce) == "58f0362c355a6624fff9f0b84d47591c570263908832294375b7bf27731628e5"
    body = b'{"external_order_id":"TEST-0001","items":[{"sku_id":"S000001","quantity":1,"expected_unit_price":"9.25"}]}'
    assert hashlib.sha256(body).hexdigest() == "5814ffcdadfa9eb69348150f9fd6895c00b4c37cf6cd0202b83174354645023e"
    assert sign(secret, "POST", "/api/v1/orders", body, ts, nonce) == "e6e45d09ed271d8d721701b560d56a6f5104fd8a52aaad5380166f432bba6e89"
    print("self-test passed")


if __name__ == "__main__":
    self_test()
    if os.environ.get("CARDV_KEY_ID") and os.environ.get("CARDV_SIGNING_SECRET"):
        client = CardV(os.environ.get("CARDV_BASE_URL", "https://sandbox.cardv.net"), os.environ["CARDV_KEY_ID"], os.environ["CARDV_SIGNING_SECRET"])
        response = client.get("/api/v1/balance")
        print(response.status_code, response.text)
