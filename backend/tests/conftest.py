"""Shared test fixtures for the Marco backend test suite."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from database.database import Base, get_db
import database.models  # noqa: F401 — register ORM models with Base.metadata
from main import app


@pytest.fixture()
def db_session():
    """Provide an in-memory SQLite session that is rolled back after each test."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(db_session):
    """FastAPI TestClient wired to the in-memory test database."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_raw_call() -> dict:
    """A valid raw call payload matching sample_call.json."""
    return {
        "call_id": "DLR-00421",
        "dealer_id": "DLR-00421",
        "name": "Jane Smith",
        "phone": "555-867-5309",
        "transcript": (
            "Agent greeted the debtor Jane Smith. Debtor acknowledged the outstanding "
            "balance of $4,200. Debtor stated they will pay $500 by end of month. "
            "Agent confirmed the arrangement and reminded of next steps."
        ),
        "duration": 372,
        "timestamp": "2026-03-12T14:30:00",
        "past_due": 45,
        "original_balance": 4200.00,
        "outstanding_amount": 4200.00,
        "promise_amount": 500.00,
        "compliance_flags": "TCPA_OK",
        "dispute_flag": False,
        "sentiment_raw": "0.72",
    }
