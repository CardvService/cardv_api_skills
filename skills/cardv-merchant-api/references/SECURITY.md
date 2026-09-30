# Security

Your signing secret can spend your wallet and read card codes.
Protect it, and the codes you receive, like bank details and cash.

Related: [Authentication](AUTHENTICATION.md) · [Webhooks](WEBHOOKS.md) · [Sandbox](SANDBOX.md)

## Your secrets

| Secret | Why it matters | Keep it in |
| --- | --- | --- |
| Signing secret (`cs_live_...`) | Anyone with it can place orders and read codes. | A secret manager, on servers only |
| Webhook secret (`whsec_...`) | Proves a webhook really came from CardV. | Your webhook server only |
| Portal passwords | Owners can create and disable keys. | A password manager, with 2FA |

- Keep keys on your servers only.
  Never put them in apps, browsers, URLs, code repositories, tickets, chat or email.
- Use one key per system, so you can disable one without stopping the others.
- Limit who can read the key. Change it when someone with access leaves.
- **If a key may have leaked, disable it in the Portal at once.**
  Then create a new one and tell CardV support.
- Turn on two-step verification (2FA) for every Portal Owner.

## Codes and customer data

`GET /orders/{order_id}` returns **full, usable codes** when called with an API key.
Codes include card numbers, PINs, security codes, QR data and redeem links.
The order also echoes your customer's top-up details (`inputs`).

- **Never log** order responses, codes, redeem links or customer `inputs`.
  Log IDs instead: `order_id`, `external_order_id`, `sku_id` and the HTTP status.
- Never log the `X-Api-Key`, `X-Signature` or `X-CardV-Signature` headers.
- Store codes encrypted. Only the process that delivers them to customers should read them.
  Delete them after your retention period.
- Do not cache order responses in shared caches, CDNs or monitoring tools.
  Turn off body capture for CardV calls.
- A `redeem_url` **is** the code. Protect it like a PIN.

## Network

- Call only `b2b.cardv.net` and `sandbox.cardv.net`, over HTTPS. Never turn off certificate checks.
- Use the [IP allowlist](AUTHENTICATION.md#ip-allowlist) in production.
  It limits the damage if a key leaks. Update it when your servers change.
- Check every webhook signature, reject old timestamps and ignore duplicates.
  Do not put your webhook URL behind a login. The signature is the proof.

## People and access

- Give each Portal user the lowest role they need:
  Viewer to look, Manager to order and fund, Owner to manage security.
- Remove people from the Portal when they leave, in both Live and Sandbox.

## Audit log

The Portal's audit log (Owner) records security actions,
such as key creation, key reveals of legacy keys, IP allowlist changes and webhook secret changes.
CardV also records blocked IPs, signature failures and rate-limit hits,
and its team is alerted on unusual activity.

Check the audit log regularly. Treat any key creation or reveal you did not expect as a possible leak.

## Reporting a problem

If you suspect a leaked key, fraudulent orders or a security issue at CardV,
email `service@cardv.net` at once. Include your Merchant ID and the order IDs.
**Never** include the secrets themselves.
