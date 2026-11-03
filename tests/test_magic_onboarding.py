"""Analyse invitée, preuve de propriété e-mail et rattachement privé."""
import re
from datetime import datetime, timedelta, timezone

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import GUEST_COOKIE, token_digest
from app.main import app
from app.models.analysis import Analysis
from app.models.user import MagicLink, User, UserSession
from test_accounts_history import register, upload


def mail_capture(monkeypatch):
    sent = []
    def fake_post(url, **options):
        sent.append(options["json"])
        return httpx.Response(200, json={"id": "fake-mail-id"})
    monkeypatch.setattr(httpx, "post", fake_post)
    return sent


def token_from(message):
    return re.search(r"#verify/([A-Za-z0-9_-]{40,128})", message["text"])[1]


def consume(client, token):
    return client.post("/auth/magic/consume", json={"token": token})


def test_guest_report_is_not_public(client, db):
    report = upload(client).json()
    with Session(db) as session:
        row = session.get(Analysis, report["id"])
        assert row.user_id is None
        assert row.guest_hash == token_digest(client.cookies.get(GUEST_COOKIE))
    with TestClient(app, base_url="https://testserver", headers={"X-CSRF-Protection": "1"}) as stranger:
        assert stranger.get(f"/analyses/{report['id']}").status_code == 404
        assert stranger.post(f"/analyses/{report['id']}/email", json={"email": "attacker@example.com"}).status_code == 404
    assert client.get(f"/analyses/{report['id']}").status_code == 200


def test_account_created_only_after_confirmation_and_link_single_use(client, db, monkeypatch):
    messages = mail_capture(monkeypatch)
    report = upload(client).json()
    reply = client.post(f"/analyses/{report['id']}/email", json={"email": "Alice@Example.com"})
    assert reply.status_code == 200, reply.text
    token = token_from(messages[0])
    assert token not in reply.text
    assert messages[0]["to"] == ["alice@example.com"]
    assert len(messages[0]["attachments"]) == 1
    with Session(db) as session:
        assert session.scalar(select(User)) is None
        assert session.get(MagicLink, token_digest(token)) is not None
        assert session.get(Analysis, report["id"]).user_id is None
    # Aperçu non destructif : les scanners de liens ne créent ni compte ni session.
    for _ in range(2):
        assert client.post("/auth/magic/preview", json={"token": token}).json()["email"] == "alice@example.com"
    assert client.get("/auth/me").status_code == 401
    result = consume(client, token)
    assert result.status_code == 200, result.text
    assert result.json()["analysis_id"] == report["id"]
    assert client.get("/auth/me").json()["email"] == "alice@example.com"
    assert [row["id"] for row in client.get("/analyses").json()] == [report["id"]]
    assert consume(client, token).status_code == 400
    with Session(db) as session:
        row = session.get(Analysis, report["id"])
        assert row.user_id == result.json()["id"] and row.guest_hash is None
        assert session.get(User, row.user_id).verified_at is not None


def test_confirmation_can_happen_in_another_browser(client, monkeypatch):
    messages = mail_capture(monkeypatch)
    report = upload(client).json()
    client.post(f"/analyses/{report['id']}/email", json={"email": "alice@example.com"})
    with TestClient(app, base_url="https://testserver", headers={"X-CSRF-Protection": "1"}) as mailbox_browser:
        assert consume(mailbox_browser, token_from(messages[0])).status_code == 200
        assert mailbox_browser.get(f"/analyses/{report['id']}").status_code == 200
    # Le cookie invité ne permet plus d’ouvrir un rapport devenu propriété du compte.
    assert client.get(f"/analyses/{report['id']}").status_code == 404


def test_reconnect_existing_account_and_revoke_unverified_password_session(client, db, monkeypatch):
    previous_user = register(client).json()
    old_cookie = client.cookies.get("csv_check_session")
    client.post("/auth/logout")
    messages = mail_capture(monkeypatch)
    assert client.post("/auth/magic/request", json={"email": "alice@example.com"}).status_code == 200
    assert "attachments" not in messages[0]
    result = consume(client, token_from(messages[0]))
    assert result.json()["id"] == previous_user["id"]
    with Session(db) as session:
        assert len(session.scalars(select(User)).all()) == 1
        assert session.get(UserSession, token_digest(old_cookie)) is None


def test_expired_and_invalid_link(client, db, monkeypatch):
    messages = mail_capture(monkeypatch)
    client.post("/auth/magic/request", json={"email": "alice@example.com"})
    token = token_from(messages[0])
    with Session(db) as session:
        session.get(MagicLink, token_digest(token)).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
    assert consume(client, token).status_code == 400
    assert consume(client, "x" * 43).status_code == 400
    with Session(db) as session:
        assert session.scalar(select(User)) is None


def test_magic_csrf_and_invalid_email(client):
    assert client.post("/auth/magic/request", json={"email": "invalid"}).status_code == 422
    del client.headers["X-CSRF-Protection"]
    assert client.post("/auth/magic/request", json={"email": "a@example.com"}).status_code == 403
    for route in ("preview", "consume"):
        assert client.post(f"/auth/magic/{route}", json={"token": "x" * 43}).status_code == 403


def test_email_error_does_not_create_account_and_link_still_works_if_delivery_ambiguous(client, monkeypatch, db):
    captured = []
    def timeout(url, **kwargs):
        captured.append(kwargs["json"])
        raise httpx.ReadTimeout("lost response")
    monkeypatch.setattr(httpx, "post", timeout)
    result = client.post("/auth/magic/request", json={"email": "a@example.com"})
    assert result.status_code == 502
    with Session(db) as session:
        assert session.scalar(select(User)) is None
    assert consume(client, token_from(captured[0])).status_code == 200
