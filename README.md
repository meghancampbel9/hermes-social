# hermes-social

Generic agent-to-agent communication layer built on the
[A2A protocol (v1.0)](https://google.github.io/a2a/).

hermes-social is a **pipe with access control** — it handles identity,
transport, contact graph, permissions, and message storage. It never
interprets message content. The host agent (Hermes, OpenClaw, or any
A2A/MCP-compatible framework) owns all business logic.

## What it does

- **Identity**: Ed25519 keypair, A2A agent cards, JWT authentication
- **Transport**: Send and receive A2A messages over HTTP+JSON
- **Contacts**: Manage a graph of known remote agents
- **Permissions**: Per-contact allow/deny grants
- **Storage**: SQLite-backed message history (inbound + outbound)
- **MCP interface**: Tools for the host agent to send, receive, and respond
- **Webhooks**: Notify the host agent of inbound messages

## Setup

### Docker (recommended)

1. Copy `backend/.env.example` to `backend/.env` and fill in values
2. `docker compose up -d`
3. Access the management UI at the configured external URL
4. Add contacts via the UI or API
5. Connect your host agent via MCP (port 8341)
6. Install agent skills (see below)
7. Configure the agent wake-up webhook (see below)

### Agent Skills

The `skills/` directory contains Hermes agent skills that teach the agent
how to use hermes-social's MCP tools for autonomous coordination. The deploy
script (`deploy.sh`) automatically syncs these to your agent's skills directory.

For manual install, copy `skills/social/` into your agent's skills directory:

```bash
cp -r skills/social/ ~/.hermes/skills/social/
```

### Local development

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
# Backend
cd backend
uv sync --group dev        # installs runtime + test + lint deps
cp .env.example .env       # then edit .env
uv run uvicorn app.main:app --host 0.0.0.0 --port 8340
uv run uvicorn app.mcp_run:app --host 0.0.0.0 --port 8341

# Frontend (separate terminal)
cd frontend
npm ci
npm run dev                # proxies /api/* to localhost:8340

# Tests
cd backend
uv run pytest tests/
```

### Agent Wake-Up Webhook

When another agent sends a message, hermes-social needs a way to wake up
your host agent so it can process the message and respond.

hermes-social POSTs a JSON payload to `NOTIFICATION_WEBHOOK_URL` whenever
an inbound A2A message arrives. The payload includes a HMAC-SHA256 signature
in the `X-Webhook-Signature` header (using `NOTIFICATION_WEBHOOK_SECRET`).

**For Hermes Agent**, enable the built-in webhook platform adapter:

```yaml
# In the Hermes agent's config.yaml
platforms:
  webhook:
    enabled: true
    extra:
      port: 8644
      routes:
        a2a-inbox:
          secret: "<shared secret — same as NOTIFICATION_WEBHOOK_SECRET>"
          prompt: >-
            A social message arrived from {contact} (type: {data_type}).
            Data: {data}.
            Load the hermes-social-coordination skill and follow its procedure.
```

The agent will deliver output to whichever platform has an active session
(Telegram, Discord, Matrix, web terminal, etc.). To force a specific channel,
add `deliver: telegram` (or `discord`, `matrix`) and `deliver_extra` with
the channel-specific config.

The prompt is intentionally minimal — all coordination logic lives in the
`hermes-social-coordination` skill (installed from `skills/` in this repo).
This avoids conflicting instructions between the prompt and the skill.

The 120-second webhook cooldown ensures that follow-up messages during
an active negotiation don't spawn redundant agent sessions — the
already-running agent picks them up via `social_inbox`.

Then set in hermes-social's `.env`:

```
HERMES_SOCIAL_NOTIFICATION_WEBHOOK_URL=http://<hermes-agent-host>:8644/webhooks/a2a-inbox
HERMES_SOCIAL_NOTIFICATION_WEBHOOK_SECRET=<shared secret>
```

**For other frameworks**, point the webhook URL at any HTTP endpoint that
can trigger an agent run. The POST body is:

```json
{
  "event": "message_received",
  "contact": "sender name",
  "data_type": "message",
  "interaction_id": "...",
  "data": { ... }
}
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `social_send(contact_id, content, data_type)` | Send a message to a contact |
| `social_inbox(limit, data_type, contact_id)` | List recent inbound messages |
| `social_respond(interaction_id, content, data_type)` | Reply to a message |
| `social_contacts(query)` | List contacts |
| `social_contact_detail(contact_id)` | Get contact details |
| `social_interactions(data_type, status_filter, direction, limit)` | List all interactions |

## Message Flow

```
User A: "coordinate dinner with B"
  │
  ▼
Agent A                              Agent B
  │ social_send(request)               │
  ▼                                    ▼
hermes-social A ───A2A──────► hermes-social B
                                  │
                                  ├─ Store interaction
                                  └─ Webhook → Agent B (first msg only)
                                       │
                                       ▼
                              Agent B wakes up, reads inbox
                              Agent B responds autonomously
                                       │
Agent A reads inbox ◄─── A2A ──────────┘
Agent A responds   ──── A2A ──────────►  Agent B reads inbox
  ... autonomous back-and-forth ...      ... via social_inbox ...
                                       │
  ┌────────────────────────────────────┘
  ▼
Agent A: "We agreed on Thursday 7pm at X"
  │ → Present to User A → confirm?
  │
User A: "yes"
  │
Agent A → social_respond(confirmed) ──► Agent B
                                         │
                                         ▼
                                    Notify User B:
                                    "Dinner Thursday 7pm confirmed"
                                    User B: "confirmed" (or auto-ack)
                                         │
                                         ▼
Agent A notified ◄── A2A ── final ack ──┘
  │
User A: "All set!"
```

The webhook cooldown (120s) ensures only the **first** inbound message
from a new conversation triggers an agent wake-up. All subsequent messages
during active negotiation are picked up by the already-running agent
via `social_inbox` polling.

## Configuration

All settings use the `HERMES_SOCIAL_` env prefix:

| Variable | Description |
|----------|-------------|
| `EXTERNAL_URL` | Public URL for this instance |
| `AGENT_NAME` | Display name in agent card |
| `OWNER_NAME` | Owner name in agent card |
| `JWT_SECRET` | Secret for UI auth tokens |
| `NOTIFICATION_WEBHOOK_URL` | Where to POST inbound message notifications |
| `NOTIFICATION_WEBHOOK_SECRET` | HMAC-SHA256 secret for webhook signature |
| `MCP_ENABLED` | Enable MCP server (default: true) |

## Architecture

See [DESIGN.md](DESIGN.md) for the full architecture documentation.
