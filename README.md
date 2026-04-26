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

1. Copy `.env.example` to `.env` and configure
2. `docker compose up -d`
3. Access the management UI at the configured external URL
4. Add contacts via the UI or API
5. Connect your host agent via MCP (port 8341)
6. Configure the agent wake-up webhook (see below)

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
          deliver: telegram          # deliver agent output to Telegram
          deliver_extra:
            chat_id: "<your telegram chat id>"  # from channel_directory.json
          prompt: >-
            You received a social message from {contact} (type: {data_type}).
            Message data: {data}.
            IMPORTANT: Present this message to the user in a clear summary.
            If it requires a commitment (meeting, event, agreement), ask the
            user for explicit confirmation before responding via social_respond.
            For informational messages, you may acknowledge automatically
            using social_respond.
```

The `deliver: telegram` setting ensures all agent activity from inbound
A2A messages is visible to the user. The prompt instructs the agent to
ask for human confirmation before making commitments.

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
Agent A                          Agent B
  │                                │
  │ social_send("hello")           │
  ▼                                ▼
hermes-social A ──A2A──► hermes-social B
                              │
                              ├─ Auth (JWT + contact lookup)
                              ├─ Grant check
                              ├─ Store interaction
                              ├─ Webhook → Agent B
                              └─ Return ack
                                   │
Agent B reads social_inbox() ◄─────┘
Agent B calls social_respond() ────► hermes-social A
```

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
