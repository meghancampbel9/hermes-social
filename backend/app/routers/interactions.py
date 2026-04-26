from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.deps import CurrentUser
from app.models import Contact, InteractionContext

router = APIRouter(prefix="/interactions", tags=["interactions"])


class InteractionOut(BaseModel):
    id: str
    data_type: str
    contact_id: str
    contact_name: str
    direction: str
    status: str
    context_data: dict
    a2a_task_id: str
    created_at: str
    updated_at: str


def _ictx_to_out(ictx: InteractionContext, session: Session) -> InteractionOut:
    contact = session.get(Contact, ictx.contact_id)
    return InteractionOut(
        id=ictx.id,
        data_type=ictx.data_type,
        contact_id=ictx.contact_id,
        contact_name=contact.name if contact else "Unknown",
        direction=ictx.direction,
        status=ictx.status,
        context_data=json.loads(ictx.context_data),
        a2a_task_id=ictx.a2a_task_id,
        created_at=ictx.created_at.isoformat(),
        updated_at=ictx.updated_at.isoformat(),
    )


@router.get("", response_model=list[InteractionOut])
def list_interactions(
    user: CurrentUser,
    data_type: str | None = None,
    direction: str | None = None,
    status_filter: str | None = None,
    session: Session = Depends(get_session),
):
    stmt = select(InteractionContext).order_by(InteractionContext.created_at.desc())
    if data_type:
        stmt = stmt.where(InteractionContext.data_type == data_type)
    if direction:
        stmt = stmt.where(InteractionContext.direction == direction)
    if status_filter:
        stmt = stmt.where(InteractionContext.status == status_filter)
    interactions = session.exec(stmt).all()
    return [_ictx_to_out(i, session) for i in interactions]


@router.get("/{interaction_id}", response_model=InteractionOut)
def get_interaction(interaction_id: str, user: CurrentUser, session: Session = Depends(get_session)):
    ictx = session.get(InteractionContext, interaction_id)
    if ictx is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interaction not found")
    return _ictx_to_out(ictx, session)
