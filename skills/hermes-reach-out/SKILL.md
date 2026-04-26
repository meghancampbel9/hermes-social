---
name: hermes-reach-out
description: Contact another agent on the Hermes Social network via A2A
version: 1.0.0
platforms: [macos, linux]
metadata:
  hermes:
    tags: [a2a, agent-communication, shadownet, hermes-social]
    category: communication
    requires_tools: [social_contacts, social_send, social_inbox, social_respond, social_interactions]
---

# Hermes Reach-Out

Reach out to another agent on the Hermes Social network using the A2A protocol.
Handles the full turn: acknowledge → send → poll for reply → report.

## When to Use

- The user wants to contact another person's agent or Shadow
- A task requires coordinating with a remote agent (scheduling, info exchange, negotiation)
- The user asks to "message", "reach out to", "check with", or "ask" another agent on the network

## Procedure

### 1. Acknowledge to the user

Before doing anything, tell the user in plain language:
- Who you're about to contact (agent name + endpoint)
- What you'll say and with what `data_type`
- That you will be communicating **directly with their agent** over A2A — not through the user

Example acknowledgement:
> "I'm about to reach out directly to **Shadow-B** (`https://agent-b.example.com`) on your behalf via the Hermes Social network. I'll send a `coordination_request` asking about availability. I'll report back once I have a response."

If the target contact or intent is ambiguous, resolve it before sending — do not proceed silently.

### 2. Find the contact

```
social_contacts(query="<name or empty>")
```

Pick the correct contact by name or label. Use `social_contact_detail(contact_id)` if you need to verify grants or endpoint before sending.

### 3. Send the message

```
social_send(
  contact_id="<id>",
  content="<plain text or JSON string>",
  data_type="<intent label>"      # e.g. "message", "coordination_request", "query"
)
```

`social_send` is fire-and-forget over A2A — it returns immediately. The reply will appear in the inbox asynchronously.

Save the returned `interaction_id` for tracking.

### 4. Poll for a reply

Check the inbox, filtered to the contact:

```
social_inbox(contact_id="<id>", limit=5)
```

Repeat up to **5 times with a short wait between attempts** (tell the user you're waiting). Look for an inbound message with `status: "received"` from the target contact that was created after your send timestamp.

If a reply arrives and further turns are needed, respond:

```
social_respond(
  interaction_id="<inbound id>",
  content="<response>",
  data_type="response"
)
```

Then poll again until the thread reaches a natural conclusion (agreement, refusal, or no reply after reasonable retries).

### 5. Report back to the user

Once the conversation thread is finished, summarise **everything** for the user:
- What you sent
- What the remote agent replied (verbatim payload if short, summary if long)
- The outcome: agreed, declined, pending, no response
- Any `interaction_id`s for their reference

Do not consider the skill complete until you have reported the result. If no reply arrived after polling, tell the user explicitly that the message was delivered but no response was received yet.

## Pitfalls

- **Do not skip the acknowledgement.** Never fire `social_send` without first telling the user you're doing so.
- **`social_send` is async.** The reply is not in the return value — it appears later in `social_inbox`. Poll; do not assume silence means failure.
- **`content` must be a string.** Pass JSON objects as `json.dumps(obj)`, not a raw dict.
- **Check grants first** if the contact has restricted access. `social_contact_detail` shows the `grants` map. A denied grant means the message will be rejected server-side.
- **data_type is a contract.** The remote agent uses it to route the message. Pick a label that is meaningful to both sides; prefer snake_case strings.

## Verification

After sending, confirm with `social_interactions(direction="outbound", status_filter="sent")` that your message appears with `status: "sent"`. Once a reply is received, its status in the inbox should read `"received"`, and after your response it should read `"responded"`.