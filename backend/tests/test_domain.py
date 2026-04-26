"""Tests for the generic A2A communication layer.

Covers: grant enforcement, contact identification, inbound message handling,
and the simplified data model.
"""

from __future__ import annotations

import json

import pytest
from sqlmodel import Session

from app.grants import GrantDenied, enforce_grant, identify_sender
from app.models import AccessGrant, Contact, GrantType, InteractionContext

# ── Grant Enforcement ───────────────────────────────────────────────────────


class TestGrants:
    def test_grant_allowed(self, db_session: Session, contact: Contact):
        grant = AccessGrant(
            contact_id=contact.id,
            grant_type=GrantType.messaging,
            allowed=True,
        )
        db_session.add(grant)
        db_session.commit()
        enforce_grant(db_session, contact)

    def test_grant_denied_no_grant(self, db_session: Session, contact: Contact):
        with pytest.raises(GrantDenied):
            enforce_grant(db_session, contact)

    def test_grant_denied_explicitly_disabled(self, db_session: Session, contact: Contact):
        grant = AccessGrant(
            contact_id=contact.id,
            grant_type=GrantType.messaging,
            allowed=False,
        )
        db_session.add(grant)
        db_session.commit()
        with pytest.raises(GrantDenied):
            enforce_grant(db_session, contact)

    def test_identify_sender(self, db_session: Session, contact: Contact):
        found = identify_sender(db_session, "AAAA")
        assert found is not None
        assert found.id == contact.id

    def test_identify_sender_unknown(self, db_session: Session):
        found = identify_sender(db_session, "UNKNOWN_KEY")
        assert found is None


# ── Data Model ──────────────────────────────────────────────────────────────


class TestDataModel:
    def test_contact_metadata(self, db_session: Session):
        c = Contact(
            name="Bob",
            agent_endpoint="http://bob:8340",
            metadata_json=json.dumps({"relationship": "colleague", "shared_interests": ["AI"]}),
        )
        db_session.add(c)
        db_session.commit()
        db_session.refresh(c)
        meta = json.loads(c.metadata_json)
        assert meta["relationship"] == "colleague"
        assert "AI" in meta["shared_interests"]

    def test_interaction_context_stores_data(self, db_session: Session, contact: Contact):
        ictx = InteractionContext(
            data_type="custom_request",
            contact_id=contact.id,
            direction="inbound",
            status="received",
            context_data=json.dumps({"key": "value"}),
        )
        db_session.add(ictx)
        db_session.commit()
        db_session.refresh(ictx)
        assert ictx.data_type == "custom_request"
        assert ictx.direction == "inbound"
        data = json.loads(ictx.context_data)
        assert data["key"] == "value"

    def test_interaction_outbound(self, db_session: Session, contact: Contact):
        ictx = InteractionContext(
            data_type="message",
            contact_id=contact.id,
            direction="outbound",
            status="sent",
            context_data=json.dumps({"text": "hello"}),
        )
        db_session.add(ictx)
        db_session.commit()
        db_session.refresh(ictx)
        assert ictx.direction == "outbound"
        assert ictx.status == "sent"


# ── A2A Protocol Helpers ────────────────────────────────────────────────────


class TestA2AHelpers:
    def test_build_a2a_message(self):
        from app.executor import build_a2a_message

        msg = build_a2a_message("test_type", {"key": "val"})
        assert "message" in msg
        parts = msg["message"]["parts"]
        assert len(parts) == 1
        assert parts[0]["data"]["type"] == "test_type"
        assert parts[0]["data"]["key"] == "val"

    def test_build_a2a_message_with_task_id(self):
        from app.executor import build_a2a_message

        msg = build_a2a_message("test_type", {}, task_id="task-123")
        assert msg["message"]["taskId"] == "task-123"

    def test_extract_data_part(self):
        from app.executor import extract_data_part

        body = {
            "message": {
                "parts": [{"data": {"type": "foo", "bar": 1}, "mediaType": "application/json"}]
            }
        }
        dtype, data = extract_data_part(body)
        assert dtype == "foo"
        assert data["bar"] == 1

    def test_extract_text_part(self):
        from app.executor import extract_data_part

        body = {"message": {"parts": [{"text": "hello"}]}}
        dtype, data = extract_data_part(body)
        assert dtype == "message"
        assert data["text"] == "hello"

    def test_message_response(self):
        from app.executor import data_part, message_response

        resp = message_response(data_part("ack", {"received": True}))
        assert "message" in resp
        assert resp["message"]["role"] == "ROLE_AGENT"
        parts = resp["message"]["parts"]
        assert parts[0]["data"]["type"] == "ack"

    def test_task_response(self):
        from app.executor import task_response

        resp = task_response("task-1", "TASK_STATE_COMPLETED")
        assert resp["task"]["id"] == "task-1"
        assert resp["task"]["status"]["state"] == "TASK_STATE_COMPLETED"
