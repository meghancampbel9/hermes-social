from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.test"), override=True)
from sqlmodel import Session, SQLModel, create_engine

from app.models import Contact


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def contact(db_session: Session) -> Contact:
    c = Contact(
        name="Alice",
        agent_endpoint="http://alice:8340",
        agent_public_key="AAAA",
        label="friend",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c
