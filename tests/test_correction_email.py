import base64
import csv
from io import StringIO

import httpx
import pytest
from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.services.csv_analyzer import analyze_csv
from app.services.csv_corrector import correct_csv
from test_accounts_history import register, upload


@pytest.mark.parametrize("delimiter", [",", ";"])
def test_correction_preserves_values_and_only_removes_exact_duplicates(delimiter):
    rows = [["name", "note"], ["Alice", "hello\nworld"], ["Bob", ""], ["Bob", " "], ["Alice", "hello\nworld"], ["alice", "hello\nworld"]]
    source = StringIO(newline="")
    writer = csv.writer(source, delimiter=delimiter)
    writer.writerows(rows)
    source.write("\r\n")
    content = source.getvalue().encode("utf-8-sig")
    assert analyze_csv(content, delimiter)["duplicate_count"] == 1
    result = correct_csv(content, delimiter)
    decoded = list(csv.reader(StringIO(result.decode("utf-8-sig"), newline=""), delimiter=delimiter))
    assert decoded == rows[:4] + rows[5:]
    assert analyze_csv(result, delimiter)["duplicate_count"] == 0
    assert analyze_csv(result, delimiter)["empty_cell_count"] == 2


def test_header_only_correction():
    assert correct_csv(b"name,email\n").decode("utf-8-sig") == "name,email\r\n"


def test_email_recipient_attachment_and_idempotent_endpoint(client, monkeypatch):
    register(client)
    report = upload(client).json()
    calls = []

    def fake_send(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json={"id": "fake-provider-message-id"})

    monkeypatch.setattr(httpx, "post", fake_send)
    response = client.post(f"/analyses/{report['id']}/email", json={"recipient": "someone-else@example.com"})
    assert response.status_code == 200
    assert response.json()["email_sent_at"]
    assert len(calls) == 1
    url, options = calls[0]
    assert url == "https://api.resend.com/emails"
    assert options["json"]["to"] == ["alice@example.com"]
    content = base64.b64decode(options["json"]["attachments"][0]["content"])
    assert analyze_csv(content)["row_count"] == 2
    assert analyze_csv(content)["empty_cell_count"] == 1
    assert options["headers"]["Idempotency-Key"].startswith("csv-check-")
    assert client.post(f"/analyses/{report['id']}/email").status_code == 200
    assert len(calls) == 1
    assert client.get(f"/analyses/{report['id']}").json()["email_sent_at"]


def test_email_failure_retry_uses_same_key_and_limit(client, monkeypatch):
    register(client)
    report = upload(client).json()
    keys = []

    def refuse(url, **kwargs):
        keys.append(kwargs["headers"]["Idempotency-Key"])
        return httpx.Response(403, json={"message": "Provider secret must not leak"})

    monkeypatch.setattr(httpx, "post", refuse)
    for _ in range(5):
        result = client.post(f"/analyses/{report['id']}/email")
        assert result.status_code == 502
        assert "secret" not in result.text
    assert len(set(keys)) == 1
    assert client.post(f"/analyses/{report['id']}/email").status_code == 429
    assert client.get(f"/analyses/{report['id']}").json()["email_sent_at"] is None


def test_missing_mail_config_and_legacy_correction(client, monkeypatch, db):
    register(client)
    report = upload(client).json()
    monkeypatch.delenv("RESEND_API_KEY")
    assert client.post(f"/analyses/{report['id']}/email").status_code == 503
    with Session(db) as session:
        analysis = session.get(Analysis, report["id"])
        analysis.corrected_csv = None
        analysis.correction_key = None
        session.commit()
    assert client.post(f"/analyses/{report['id']}/email").status_code == 409


def test_email_timeout_not_marked_sent(client, monkeypatch):
    register(client)
    report = upload(client).json()

    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(httpx, "post", timeout)
    assert client.post(f"/analyses/{report['id']}/email").status_code == 502
    assert client.get(f"/analyses/{report['id']}").json()["email_sent_at"] is None
