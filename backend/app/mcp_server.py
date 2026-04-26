"""MCP server exposing generic agent-to-agent communication tools.

Uses FastMCP for tool definitions and mounts into the FastAPI app
via streamable_http_app().
"""
from __future__ import annotations

import asyncio
import json
import logging

from mcp.server.fastmcp import FastMCP
from sqlmodel import Session, select

from app.config import settings
from app.database import engine
from app.models import AccessGrant, Contact, InteractionContext, _utcnow

logger = logging.getLogger(__name__)

mcp = FastMCP("hermes-social", stateless_http=True)


def _get_session() -> Session:
    return Session(engine)


# ── Tools ──────────────────────────────────────────────────────────────────


@mcp.tool()
def social_contacts(query: str = "") -> str:
    """List contacts in the user's agent network.

    Returns the id, name, endpoint, and metadata for each contact.
    Use the 'id' field when calling social_send() or other tools.
    Optionally filter by name substring.
    """
    with _get_session() as session:
        contacts = session.exec(select(Contact)).all()
        results = []
        for c in contacts:
            if query and query.lower() not in c.name.lower():
                continue
            results.append({
                "id": c.id,
                "name": c.name,
                "agent_endpoint": c.agent_endpoint,
                "label": c.label,
                "metadata": json.loads(c.metadata_json),
            })
        return json.dumps(results, indent=2)


@mcp.tool()
def social_contact_detail(contact_id: str) -> str:
    """Get full details on a specific contact including their access grants."""
    with _get_session() as session:
        contact = session.get(Contact, contact_id)
        if contact is None:
            return json.dumps({"error": "Contact not found"})
        grants = session.exec(select(AccessGrant).where(AccessGrant.contact_id == contact_id)).all()
        return json.dumps({
            "id": contact.id,
            "name": contact.name,
            "agent_endpoint": contact.agent_endpoint,
            "label": contact.label,
            "notes": contact.notes,
            "metadata": json.loads(contact.metadata_json),
            "grants": {g.grant_type: g.allowed for g in grants},
        }, indent=2)


@mcp.tool()
def social_send(contact_id: str, content: str, data_type: str = "message") -> str:
    """Send a message to another agent via the A2A protocol.

    This is the primary tool for agent-to-agent communication. Use it to
    send any kind of message — coordination requests, queries, availability
    checks, or freeform text. The remote agent will receive it and may
    respond; check social_inbox() afterward for replies.

    Args:
        contact_id: The contact to send to (get from social_contacts).
        content: The message payload — a JSON string for structured data,
                 or plain text for simple messages.
        data_type: A label describing this message's purpose. Use any string
                   that helps the remote agent understand the intent, e.g.
                   "message", "coordination_request", "availability_check",
                   "query", or any custom type you define.

    Workflow:
        1. Call social_send() to send a message
        2. Call social_inbox() to check for the reply
        3. If needed, continue the conversation with more social_send() calls
    """
    with _get_session() as session:
        contact = session.get(Contact, contact_id)
        if contact is None:
            return json.dumps({"error": "Contact not found"})

        from app.executor import build_a2a_message, send_a2a_message

        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            payload = {"text": content}

        body = build_a2a_message(data_type, payload)
        msg_id = body["message"]["messageId"]
        endpoint = contact.agent_endpoint

        ictx = InteractionContext(
            data_type=data_type,
            contact_id=contact.id,
            direction="outbound",
            status="sent",
            context_data=json.dumps(payload),
        )
        session.add(ictx)
        session.commit()
        session.refresh(ictx)

    async def _deliver():
        return await send_a2a_message(endpoint, body)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_deliver())
    except RuntimeError:
        pass

    return json.dumps({"sent": True, "message_id": msg_id, "interaction_id": ictx.id})


@mcp.tool()
def social_inbox(limit: int = 20, data_type: str = "", contact_id: str = "") -> str:
    """Check for inbound messages from other agents.

    Call this to see if any agent has sent you a message, query, or request.
    Each message has an 'id' you can use with social_respond() to reply.

    Messages with status 'received' have not been responded to yet.
    After you call social_respond(), their status changes to 'responded'.

    Args:
        limit: Max number of messages to return (default 20).
        data_type: Filter by message type (e.g. "coordination_request").
        contact_id: Filter by a specific contact.
    """
    with _get_session() as session:
        stmt = (
            select(InteractionContext)
            .where(InteractionContext.direction == "inbound")
            .order_by(InteractionContext.created_at.desc())
            .limit(limit)
        )
        if data_type:
            stmt = stmt.where(InteractionContext.data_type == data_type)
        if contact_id:
            stmt = stmt.where(InteractionContext.contact_id == contact_id)
        interactions = session.exec(stmt).all()
        results = []
        for i in interactions:
            contact = session.get(Contact, i.contact_id) if i.contact_id else None
            results.append({
                "id": i.id,
                "data_type": i.data_type,
                "contact": contact.name if contact else "Unknown",
                "contact_id": i.contact_id,
                "status": i.status,
                "data": json.loads(i.context_data),
                "created_at": i.created_at.isoformat(),
            })
        return json.dumps(results, indent=2)


@mcp.tool()
def social_respond(interaction_id: str, content: str, data_type: str = "response") -> str:
    """Reply to an inbound message from another agent.

    Use the 'id' field from social_inbox() results as the interaction_id.
    The reply is sent back to the original sender via A2A.

    Args:
        interaction_id: The id of the inbound message to reply to.
        content: The response payload — a JSON string for structured data,
                 or plain text.
        data_type: A label for the response type (e.g. "response",
                   "availability_response", "confirmation").
    """
    with _get_session() as session:
        ictx = session.get(InteractionContext, interaction_id)
        if ictx is None:
            return json.dumps({"error": "Interaction not found"})

        contact = session.get(Contact, ictx.contact_id) if ictx.contact_id else None
        if contact is None:
            return json.dumps({"error": "Contact not found"})

        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            payload = {"text": content}

        ctx_data = json.loads(ictx.context_data)
        ctx_data["response"] = payload
        ictx.context_data = json.dumps(ctx_data)
        ictx.status = "responded"
        ictx.updated_at = _utcnow()
        session.add(ictx)
        session.commit()

        from app.executor import build_a2a_message, send_a2a_message

        endpoint = contact.agent_endpoint
        task_id = ictx.a2a_task_id or None
        interaction_id = ictx.id

        body = build_a2a_message(data_type, payload, task_id=task_id)

    async def _deliver():
        return await send_a2a_message(endpoint, body)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_deliver())
    except RuntimeError:
        pass

    return json.dumps({"responded": True, "interaction_id": interaction_id})


@mcp.tool()
def social_interactions(data_type: str = "", status_filter: str = "",
                        direction: str = "", limit: int = 20) -> str:
    """List all interactions. Optionally filter by data_type, status, or direction."""
    with _get_session() as session:
        stmt = select(InteractionContext).order_by(InteractionContext.created_at.desc())
        if data_type:
            stmt = stmt.where(InteractionContext.data_type == data_type)
        if status_filter:
            stmt = stmt.where(InteractionContext.status == status_filter)
        if direction:
            stmt = stmt.where(InteractionContext.direction == direction)
        interactions = session.exec(stmt.limit(limit)).all()
        results = []
        for i in interactions:
            contact = session.get(Contact, i.contact_id) if i.contact_id else None
            results.append({
                "id": i.id,
                "data_type": i.data_type,
                "contact": contact.name if contact else "Unknown",
                "contact_id": i.contact_id,
                "direction": i.direction,
                "status": i.status,
                "data": json.loads(i.context_data),
                "created_at": i.created_at.isoformat(),
                "updated_at": i.updated_at.isoformat(),
            })
        return json.dumps(results, indent=2)
