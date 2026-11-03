"""Sessions opaques en cookie HttpOnly et protection des mutations."""
import hashlib
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import COOKIE_NAME, COOKIE_SECURE, SESSION_DAYS
from app.database import engine
from app.models.user import User, UserSession

password_hash = PasswordHash.recommended()
dummy_hash = password_hash.hash(secrets.token_urlsafe(32))
_attempts: dict[str, list[float]] = {}
_attempts_lock = threading.Lock()


def require_csrf(x_csrf_protection: str | None = Header(default=None)) -> None:
    """Exiger un en-tête non simple ; aucune origine CORS externe n’est autorisée."""
    if x_csrf_protection != "1":
        raise HTTPException(403, "Requête refusée : en-tête de protection manquant.")


def rate_limit(key: str, maximum: int, seconds: int = 900) -> None:
    """Frein local aux essais répétés ; prévu pour un seul processus Uvicorn."""
    now = time.monotonic()
    with _attempts_lock:
        for old_key in list(_attempts):
            _attempts[old_key] = [stamp for stamp in _attempts[old_key] if stamp > now - 3600]
            if not _attempts[old_key]:
                del _attempts[old_key]
        recent = [stamp for stamp in _attempts.get(key, []) if stamp > now - seconds]
        if len(recent) >= maximum:
            raise HTTPException(429, "Trop de tentatives. Réessayez plus tard.")
        _attempts[key] = recent + [now]


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(session: Session, user_id: int, request: Request, response: Response) -> None:
    now = datetime.now(timezone.utc)
    session.execute(delete(UserSession).where(UserSession.expires_at <= now))
    old_token = request.cookies.get(COOKIE_NAME)
    if old_token:
        session.execute(delete(UserSession).where(UserSession.token_hash == token_digest(old_token)))
    token = secrets.token_urlsafe(32)
    session.add(UserSession(
        token_hash=token_digest(token), user_id=user_id,
        expires_at=now + timedelta(days=SESSION_DAYS),
    ))
    session.commit()
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_DAYS * 86400,
        httponly=True, secure=COOKIE_SECURE, samesite="strict", path="/",
    )


def get_current_user(request: Request) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 128:
        raise HTTPException(401, "Connectez-vous pour continuer.")
    with Session(engine) as session:
        user = session.scalar(
            select(User).join(UserSession, UserSession.user_id == User.id).where(
                UserSession.token_hash == token_digest(token),
                UserSession.expires_at > datetime.now(timezone.utc),
            )
        )
        if user is None:
            raise HTTPException(401, "Votre session a expiré. Reconnectez-vous.")
        return user


GUEST_COOKIE = "csv_check_guest"


def get_optional_user(request: Request) -> User | None:
    try:
        return get_current_user(request)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        return None


def guest_digest(request: Request) -> str | None:
    token = request.cookies.get(GUEST_COOKIE, "")
    return token_digest(token) if 32 <= len(token) <= 128 else None


def ensure_guest(request: Request, response: Response) -> str:
    existing = guest_digest(request)
    if existing:
        return existing
    token = secrets.token_urlsafe(32)
    response.set_cookie(GUEST_COOKIE, token, max_age=7 * 86400, httponly=True,
                        secure=COOKIE_SECURE, samesite="strict", path="/")
    return token_digest(token)
