---
name: hermes-social-coordination
description: Coordinate meetups between agents via Hermes Social. Handles the full flow from proposal to confirmation with minimal user interaction.
version: 3.0.0
metadata:
  hermes:
    tags: [social, coordination, meetups, scheduling, agent-to-agent]
    category: social
---

# Social Coordination

Coordinate plans (coffee, dinner, meetings) with another person's agent.

## Roles

Every coordination has an **initiator** (user asked to plan something) and
a **receiver** (contact whose agent gets the request). Follow the correct
flow for your role.

---

## INITIATOR FLOW (your user asked to plan something)

### Step 1 — Send the request

```
social_contacts(query="...") → get contact_id
social_send(contact_id, content=<JSON with activity, time, location, preferences>, data_type="coordination_request")
```

Be specific: include activity, date/time, location, preferences.

### Step 2 — Tell the user and end the session

> Sent a coordination request to Test Friend. I'll notify you when they respond.

DONE for now. Do NOT poll or sleep. When the receiver's agent responds,
a webhook will fire and start a new session automatically.

### Step 3 — Handle the response (new webhook session)

You'll be woken up with the response. Check `social_inbox()` to read it.
Present ONE clean message:

> ☕ Test Friend agreed! Coffee at Zazza (Lehrter Str 24e), Wednesday 9:30am.
> Confirm? (yes/no)

### Step 4 — Send confirmation

After user says yes:
```
social_send(contact_id, content=<plan JSON with status: "confirmed">, data_type="confirmation")
```

> Confirmed! I'll let you know when Test Friend acknowledges.

### Step 5 — Final notification (new webhook session)

When the receiver sends `confirmed`, tell the user:

> ✅ Test Friend confirmed. Coffee at Zazza, Wednesday 9:30am — you're all set.

DONE. Do not respond further.

---

## RECEIVER FLOW (another agent sent you a coordination request)

You are woken up by a webhook. The message data is in the prompt.

### Step 1 — Present the proposal to your user

Read the inbound message and present it clearly:

> Meghan wants to meet for coffee Wednesday morning at Zazza
> (Lehrter Str 24e, Berlin Mitte). What do you think?

Let the user respond. They might say "yes", "sounds good", "how about
Thursday instead?", or "no thanks".

### Step 2 — Respond to the initiator's agent

Based on user's answer:

If YES:
```
social_respond(interaction_id, content=<agreement JSON>, data_type="response")
```

If COUNTER-PROPOSAL:
```
social_respond(interaction_id, content=<counter JSON>, data_type="response")
```
Then poll for the initiator's reply and repeat.

If NO:
```
social_respond(interaction_id, content=<decline JSON>, data_type="response")
```
DONE.

### Step 3 — Wait for confirmation

After responding with agreement, end the session. When the initiator's user
confirms and their agent sends `data_type="confirmation"`, a new webhook
session starts. Notify your user:

> ✅ Meghan confirmed! Coffee at Zazza, Wednesday 9:30am — all set.

Then send back:
```
social_respond(interaction_id, content='{"status": "confirmed"}', data_type="confirmed")
```

DONE. Do not respond further.

---

## Message Types

| data_type | Sent by | Meaning |
|---|---|---|
| `coordination_request` | Initiator | "Let's plan something" |
| `response` | Receiver | Agreement, counter-proposal, or decline |
| `confirmation` | Initiator | "My user approved this plan" |
| `confirmed` | Receiver | "My user saw the confirmation, we're set" |

---

## Output Rules

- **ONE message per step.** Don't send multiple Telegram messages.
- **No narration.** Don't say "Loading skill...", "Checking inbox...", "Sending request...". Just do it and present the result.
- **No emoji walls.** One or two relevant emoji max.
- **No status updates.** Don't tell the user which step of the flow you're on.
- **Be concise.** The user wants "Coffee at X, Wed 9:30am. Confirm?" not a paragraph.

## Pitfalls

- **DO NOT POLL** — webhooks handle notifications. Never loop sleep+inbox. Send and end the session.
- **Contact IDs change** — always re-fetch before any operation.
- **STOP on confirmed** — never respond to a `confirmed` message. The conversation is done.
- **No old tools** — `social_coordinate`, `social_check_proposals`, `social_respond_proposal` do not exist.
- **One message per step** — don't send multiple Telegram messages in one session.
