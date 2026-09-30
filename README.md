# CardV skills for AI coding agents

Agent skills that teach AI coding assistants how to integrate with the [CardV Merchant API](https://cardv.net/developers/): signing requests, buying gift cards and game top-ups from your prepaid wallet, retrying safely, reading codes, verifying webhooks and running mobile recharge.

A skill is a folder with a `SKILL.md` file plus reference docs and scripts. Agents that support skills load it when the task needs it, so the generated code follows CardV's rules instead of guessing them.

| Skill | Use it for |
| --- | --- |
| [`cardv-merchant-api`](skills/cardv-merchant-api/SKILL.md) | Building, debugging or reviewing any CardV Merchant API integration |

## Install

Copy the skill folder to where your agent looks for skills.

**Claude Code**

```bash
git clone https://github.com/CardvService/cardv_api_skills.git
# for one project
mkdir -p .claude/skills && cp -r cardv_api_skills/skills/cardv-merchant-api .claude/skills/
# or for all your projects
mkdir -p ~/.claude/skills && cp -r cardv_api_skills/skills/cardv-merchant-api ~/.claude/skills/
```

**OpenAI Codex CLI**

```bash
mkdir -p ~/.codex/skills && cp -r cardv_api_skills/skills/cardv-merchant-api ~/.codex/skills/
```

**Other agents (Cursor, Windsurf, Copilot and others)**

Add `skills/cardv-merchant-api/SKILL.md` to the agent's rules or context, and keep the `references/` and `scripts/` folders next to it.

No git? Download [`cardv-merchant-api-skill.zip`](dist/cardv-merchant-api-skill.zip) and unzip it into the same folder.

## Try it

After installing, ask your agent something like:

> Using the cardv-merchant-api skill, write a Python module that buys SKU S000001 from CardV Sandbox for my order number SHOP-1001, waits for the codes, and verifies CardV webhooks.

The agent reads the skill, works in Sandbox, and follows CardV's signing, retry and security rules.

## What the skill makes the agent do

- Use Sandbox by default, and ask you before placing any Live order.
- Read keys from environment variables, never from code, and never log secrets or codes.
- Sign every request correctly and check the signing code against CardV's test vectors.
- Retry a lost order with the same order number, so you are never charged twice.
- Verify webhook signatures on the raw body before trusting them.

## Quick check

```bash
cd skills/cardv-merchant-api/scripts
python cardv_client.py              # signing self-test
python verify_webhook.py --self-test
```

With `CARDV_KEY_ID`, `CARDV_SIGNING_SECRET` and `CARDV_BASE_URL=https://sandbox.cardv.net` set, `cardv_client.py` also calls `GET /api/v1/balance`.

## Getting API access

Apply for a merchant account at [b2b.cardv.net/portal](https://b2b.cardv.net/portal/). After approval, create a Sandbox API key in the Portal (Integrations → API keys). Questions: `service@cardv.net`. Never send secrets or card codes by email.

## License

MIT. See [LICENSE](LICENSE).
