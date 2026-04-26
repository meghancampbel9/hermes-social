from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.deps import CurrentUser
from app.models import Contact, InteractionContext

router = APIRouter(prefix="/messages", tags=["messages"])


class MessageOut(BaseModel):
    id: str
    data_type: str
    contact_id: str | None
    contact_name: str
    direction: str
    status: str
    context_data: dict
    created_at: str


@router.get("", response_model=list[MessageOut])
def list_messages(
    user: CurrentUser,
    data_type: str | None = None,
    contact_id: str | None = None,
    direction: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    session: Session = Depends(get_session),
):
    stmt = (
        select(InteractionContext)
        .order_by(InteractionContext.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if data_type:
        stmt = stmt.where(InteractionContext.data_type == data_type)
    if contact_id:
        stmt = stmt.where(InteractionContext.contact_id == contact_id)
    if direction:
        stmt = stmt.where(InteractionContext.direction == direction)

    interactions = session.exec(stmt).all()
    results = []
    for i in interactions:
        contact = session.get(Contact, i.contact_id) if i.contact_id else None
        results.append(MessageOut(
            id=i.id,
            data_type=i.data_type,
            contact_id=i.contact_id,
            contact_name=contact.name if contact else "Unknown",
            direction=i.direction,
            status=i.status,
            context_data=json.loads(i.context_data),
            created_at=i.created_at.isoformat(),
        ))
    return results
