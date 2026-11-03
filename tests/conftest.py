"""Tests isolés : aucune connexion à la base réelle ni aucun e-mail envoyé."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@localhost/unused")

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import app.auth as auth_service
import app.routers.auth as auth_router
import app.routers.analyses as analyses_router
from app.database import Base
from app.main import app


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    for module in (auth_service, auth_router, analyses_router):
        monkeypatch.setattr(module, "engine", engine)
    auth_service._attempts.clear()
    monkeypatch.setenv("RESEND_API_KEY", "test-key-not-real")
    monkeypatch.setenv("EMAIL_FROM", "CSV Check <test@example.com>")
    monkeypatch.setenv("APP_URL", "https://csv-check.example.com")

    def no_network(*args, **kwargs):
        raise AssertionError("Les tests ne doivent pas envoyer d’e-mail réel")

    monkeypatch.setattr(httpx, "post", no_network)
    yield engine
    engine.dispose()


@pytest.fixture
def client(db):
    with TestClient(app, base_url="https://testserver") as client:
        client.headers["X-CSRF-Protection"] = "1"
        yield client
