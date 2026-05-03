from __future__ import annotations

import os
from contextlib import asynccontextmanager

import pytest
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.test"), override=True)

from fastapi.testclient import TestClient
from nacl.signing import SigningKey
from sqlmodel import Session, SQLModel, create_engine

from app import identity as identity_module
from app.database import get_session
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


@pytest.fixture()
def client(db_session: Session):
    from app.main import app

    @asynccontextmanager
    async def test_lifespan(app):
        key = SigningKey.generate()
        identity_module._signing_key = key
        identity_module._verify_key = key.verify_key
        yield
        identity_module._signing_key = None
        identity_module._verify_key = None

    def override_session():
        yield db_session

    app.router.lifespan_context = test_lifespan
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
