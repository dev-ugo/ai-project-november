from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import token_digest
from app.config import COOKIE_NAME
from app.models.analysis import Analysis
from app.models.user import User, UserSession

PASSWORD = "Une phrase de test 2026!"
CSV = b"name,email,city\nAlice,alice@example.com,Geneva\nBob,,Paris\nAlice,alice@example.com,Geneva\n"


def register(client, email="alice@example.com"):
    result = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert result.status_code == 201, result.text
    return result


def upload(client, filename="contacts.csv", content=CSV, delimiter=","):
    return client.post("/analyses", params={"delimiter": delimiter}, files={"file": (filename, content, "text/csv")})


def test_authentication_and_logout_revoke_cookie(client, db):
    response = register(client, "Alice@Example.com")
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=strict" in cookie
    assert response.json()["email"] == "alice@example.com"
    token = client.cookies.get(COOKIE_NAME)
    assert client.get("/auth/me").json()["email"] == "alice@example.com"
    with Session(db) as session:
        user = session.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$")
        assert PASSWORD not in user.password_hash
        assert session.get(UserSession, token_digest(token)) is not None
    assert client.post("/auth/logout").status_code == 204
    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD}).status_code == 200
    assert client.cookies.get(COOKIE_NAME, domain="testserver.local") != token


def test_invalid_credentials_and_duplicate_account(client):
    assert client.post("/auth/register", json={"email": "invalid", "password": PASSWORD}).status_code == 422
    assert client.post("/auth/register", json={"email": "alice@example.com", "password": "short"}).status_code == 422
    register(client)
    assert client.post("/auth/register", json={"email": "ALICE@example.com", "password": PASSWORD}).status_code == 409
    assert client.post("/auth/login", json={"email": "alice@example.com", "password": "An incorrect password"}).status_code == 401


def test_csrf_required_for_every_mutation(client):
    del client.headers["X-CSRF-Protection"]
    for route in ("/auth/register", "/auth/login"):
        assert client.post(route, json={"email": "alice@example.com", "password": PASSWORD}).status_code == 403
    assert client.post("/auth/logout").status_code == 403
    assert upload(client).status_code == 403
    assert client.post("/analyses/1/email").status_code == 403


def test_anonymous_can_analyze_but_has_no_account_history(client):
    report = upload(client).json()
    assert client.get("/analyses").status_code == 401
    assert client.get(f"/analyses/{report['id']}").status_code == 200
    assert client.get("/analyses/999").status_code == 404
    assert client.post("/analyses/999/email").status_code == 404


def test_private_history_and_legacy_reports(client, db):
    with Session(db) as session:
        old = Analysis(filename="legacy.csv", anomalies=[], user_id=None, correction_key=None)
        session.add(old)
        session.commit()
        legacy_id = old.id
    register(client)
    response = upload(client)
    assert response.status_code == 201
    report = response.json()
    assert (report["row_count"], report["duplicate_count"], report["empty_cell_count"]) == (3, 1, 1)
    assert report["correction_available"] is True
    assert "corrected_csv" not in report
    assert "password_hash" not in response.text
    assert response.headers["cache-control"] == "no-store"
    history = client.get("/analyses").json()
    assert [row["id"] for row in history] == [report["id"]]
    assert "anomalies" not in history[0]
    assert client.get(f"/analyses/{legacy_id}").status_code == 404
    assert client.get(f"/analyses/{report['id']}").json()["anomalies"] == report["anomalies"]
    client.post("/auth/logout")
    register(client, "bob@example.com")
    assert client.get("/analyses").json() == []
    assert client.get(f"/analyses/{report['id']}").status_code == 404
    assert client.post(f"/analyses/{report['id']}/email").status_code == 404
    assert client.get("/analyses/999999").status_code == 404


def test_session_expiry(client, db):
    register(client)
    with Session(db) as session:
        saved = session.scalar(select(UserSession))
        saved.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        session.commit()
    assert client.get("/analyses").status_code == 401


def test_history_order_and_limit(client, db):
    user_id = register(client).json()["id"]
    with Session(db) as session:
        timestamp = datetime.now(timezone.utc)
        for i in range(55):
            session.add(Analysis(user_id=user_id, filename=f"{i}.csv", created_at=timestamp))
        session.commit()
    results = client.get("/analyses").json()
    assert len(results) == 50
    assert results[0]["filename"] == "54.csv"
    assert results[-1]["filename"] == "5.csv"


def test_upload_validation(client):
    register(client)
    for content in (b"", b"a,a\n1,2", b"a,b\n1,2,3", b"a\n\xff", b"a\n\x00", b'a\n"unfinished'):
        assert upload(client, content=content).status_code == 400
    assert upload(client, filename="contacts.txt").status_code == 400
    assert upload(client, content=b"a" * (1024 * 1024 + 1)).status_code == 413
    assert upload(client, content=b"a;b\n1;2\n", delimiter=";").status_code == 201
    assert upload(client, delimiter="|").status_code == 422


def test_login_throttle(client):
    for _ in range(10):
        assert client.post("/auth/login", json={"email": "none@example.com", "password": PASSWORD}).status_code == 401
    assert client.post("/auth/login", json={"email": "none@example.com", "password": PASSWORD}).status_code == 429


def test_public_pages_and_openapi(client):
    for path in ("/", "/design-system", "/health", "/docs", "/static/js/app.js"):
        assert client.get(path).status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/analyses/{analysis_id}/email" in schema["paths"]
    assert "/auth/register" in schema["paths"]
