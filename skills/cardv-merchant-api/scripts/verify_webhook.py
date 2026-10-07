"""Verify a CardV webhook signature (Python 3.9+, standard library only).

Header format:  X-CardV-Signature: t=<unix seconds>,v2=<lowercase hex>
v2 = HMAC-SHA256(key = webhook signing secret,
                 message = "<t>.<X-CardV-Delivery>.<X-CardV-Event>." + raw body bytes)

Usage:
    python verify_webhook.py --self-test
    CARDV_WEBHOOK_SECRET=whsec_... python verify_webhook.py body.json "t=...,v2=..." <X-CardV-Delivery> <X-CardV-Event>
"""
from __future__ import annotations

import hashlib
import hmac
import os
import sys
import time


def verify(
    secret: bytes,
    raw_body: bytes,
    header: str,
    delivery: str,
    event: str,
    tolerance: int = 300,
    now: float | None = None,
) -> bool:
    try:
        parts = dict(item.split("=", 1) for item in header.split(","))
        t, v2 = parts["t"].strip(), parts["v2"].strip()
    except (KeyError, ValueError):
        return False
    current = time.time() if now is None else now
    if not t.isdigit() or abs(current - int(t)) > tolerance:
        return False
    if not delivery or not event:
        return False
    signed = f"{t}.{delivery}.{event}.".encode() + raw_body
    expected = hmac.new(secret, signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.encode(), v2.encode())  # constant time


def self_test() -> None:
    """Checks against the published test vector (fake secret)."""
    secret = b"whsec_TEST_ONLY_not_a_real_secret_000000000000"
    body = (
        b'{"event":"order.succeeded","order":{"id":"O-00000001","order_id":"O-00000001",'
        b'"external_order_id":"TEST-0001","status":"succeeded","currency":"USD","total_amount":"9.25",'
        b'"items":[{"sku_id":"S000001","product_name":"Example Card","quantity":1,"delivery_count":1}]}}'
    )
    assert len(body) == 264
    header = "t=1790000100,v2=a29bcc255a746592aacd8351a316478b6ff0d5337762ee66634635ef4100de90"
    assert verify(secret, body, header, "5521", "order.succeeded", now=1790000100)
    assert not verify(secret, body + b" ", header, "5521", "order.succeeded", now=1790000100)  # any byte change fails
    assert not verify(secret, body, header, "5522", "order.succeeded", now=1790000100)  # delivery header is signed
    assert not verify(secret, body, header, "5521", "order.refunded", now=1790000100)  # event header is signed
    assert not verify(secret, body, header, "5521", "order.succeeded", now=1790000100 + 301)  # too old
    print("self-test passed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        self_test()
    elif len(sys.argv) == 5:
        with open(sys.argv[1], "rb") as fh:
            ok = verify(os.environ["CARDV_WEBHOOK_SECRET"].encode(), fh.read(), sys.argv[2], sys.argv[3], sys.argv[4])
        print("valid" if ok else "INVALID")
        sys.exit(0 if ok else 1)
    else:
        print(__doc__)
        sys.exit(2)
