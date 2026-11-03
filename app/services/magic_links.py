"""Préparer un accès personnel à usage unique, sans créer de compte prématurément."""
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.auth import rate_limit, token_digest
from app.models.analysis import Analysis
from app.models.user import MagicLink
from app.services.email_sender import ensure_email_configured, send_access_email


def issue_link(session: Session, email: str, analysis: Analysis | None = None) -> None:
    ensure_email_configured()
    rate_limit(f"mail:{token_digest(email)}", 5, 3600)
    if analysis:
        rate_limit(f"analysis-mail:{analysis.id}", 1, 60)
    if analysis:
        session.execute(update(MagicLink).where(MagicLink.analysis_id == analysis.id, MagicLink.used_at.is_(None)).values(used_at=datetime.now(timezone.utc)))
    token = secrets.token_urlsafe(32)
    session.add(MagicLink(token_hash=token_digest(token), email=email,
                          analysis_id=analysis.id if analysis else None,
                          expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)))
    # Persister avant la requête externe : le lien reste valide si la réponse réseau est perdue.
    session.commit()
    send_access_email(email, token, analysis)
