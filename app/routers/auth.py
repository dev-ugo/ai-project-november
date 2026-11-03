"""Inscription, connexion, session courante et déconnexion."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    create_session, dummy_hash, get_current_user, password_hash,
    rate_limit, require_csrf, token_digest,
)
from app.config import COOKIE_NAME, COOKIE_SECURE
from app.database import engine
from app.models.user import MagicLink, User, UserSession

router = APIRouter(prefix="/auth", tags=["Compte"])


class Credentials(BaseModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


@router.post("/register", status_code=201, dependencies=[Depends(require_csrf)])
def register(data: Credentials, request: Request, response: Response) -> dict:
    """Créer un compte et ouvrir une session de sept jours."""
    rate_limit(f"register:{request.client.host if request.client else 'unknown'}", 10, 3600)
    with Session(engine) as session:
        user = User(email=data.email, password_hash=password_hash.hash(data.password))
        session.add(user)
        try:
            session.flush()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(409, "Un compte utilise déjà cette adresse e-mail.") from error
        user_id, email = user.id, user.email
        create_session(session, user_id, request, response)
        return {"id": user_id, "email": email}


@router.post("/login", dependencies=[Depends(require_csrf)])
def login(data: Credentials, request: Request, response: Response) -> dict:
    """Vérifier le mot de passe et renouveler le cookie de session."""
    rate_limit(f"login:{token_digest(data.email)}", 10)
    rate_limit(f"login-ip:{request.client.host if request.client else 'unknown'}", 40)
    with Session(engine) as session:
        user = session.scalar(select(User).where(User.email == data.email))
        valid = password_hash.verify(data.password, user.password_hash if user else dummy_hash)
        if not user or not valid:
            raise HTTPException(401, "Adresse e-mail ou mot de passe incorrect.")
        user_id, email = user.id, user.email
        create_session(session, user_id, request, response)
        return {"id": user_id, "email": email}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    """Retourner uniquement l’identité du compte connecté."""
    return {"id": user.id, "email": user.email}


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf)])
def logout(request: Request, response: Response) -> None:
    """Révoquer la session côté serveur et supprimer son cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        with Session(engine) as session:
            session.execute(delete(UserSession).where(UserSession.token_hash == token_digest(token)))
            session.commit()
    response.delete_cookie(COOKIE_NAME, path="/", secure=COOKIE_SECURE, httponly=True, samesite="strict")


class EmailAddress(BaseModel):
    email: EmailStr = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalize(cls, value: str) -> str:
        return value.lower()


class MagicToken(BaseModel):
    token: str = Field(min_length=40, max_length=128)


@router.post("/magic/request", dependencies=[Depends(require_csrf)])
def request_magic(data: EmailAddress, request: Request) -> dict:
    """Envoyer le même accès, que le compte existe ou non."""
    from app.services.magic_links import issue_link
    from app.services.email_sender import EmailConfigurationError, EmailDeliveryError
    rate_limit(f"magic-ip:{request.client.host if request.client else 'unknown'}", 20, 3600)
    with Session(engine) as session:
        try:
            issue_link(session, data.email)
        except EmailConfigurationError as error:
            raise HTTPException(503, str(error)) from error
        except EmailDeliveryError as error:
            raise HTTPException(502, str(error)) from error
    return {"message": "Vérifiez votre messagerie : votre lien personnel est valable 15 minutes."}


def valid_magic(session: Session, token: str, *, lock: bool = False) -> MagicLink:
    from datetime import datetime, timezone
    statement = select(MagicLink).where(
        MagicLink.token_hash == token_digest(token), MagicLink.used_at.is_(None),
        MagicLink.expires_at > datetime.now(timezone.utc),
    )
    if lock:
        statement = statement.with_for_update()
    link = session.scalar(statement)
    if link is None:
        raise HTTPException(400, "Ce lien est expiré ou a déjà été utilisé. Demandez un nouveau lien.")
    return link


@router.post("/magic/preview", dependencies=[Depends(require_csrf)])
def preview_magic(data: MagicToken) -> dict:
    """Afficher l’adresse à confirmer sans consommer le lien ni ouvrir de session."""
    with Session(engine) as session:
        link = valid_magic(session, data.token)
        return {"email": link.email}


@router.post("/magic/consume", dependencies=[Depends(require_csrf)])
def consume_magic(data: MagicToken, request: Request, response: Response) -> dict:
    """Vérifier l’adresse, rattacher son rapport, puis créer une session."""
    import secrets
    from datetime import datetime, timezone
    from sqlalchemy import update
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.models.analysis import Analysis

    with Session(engine) as session:
        # Ordre constant des verrous, y compris entre deux liens de la même adresse.
        preview = valid_magic(session, data.token)
        email = preview.email
        if session.bind.dialect.name == "postgresql":
            session.execute(pg_insert(User).values(
                email=email, password_hash=password_hash.hash(secrets.token_urlsafe(48)),
                email_attempts=0,
            ).on_conflict_do_nothing(index_elements=["email"]))
        elif session.scalar(select(User).where(User.email == email)) is None:
            session.add(User(email=email, password_hash=password_hash.hash(secrets.token_urlsafe(48))))
            session.flush()
        user = session.scalar(select(User).where(User.email == email).with_for_update())
        analysis = None
        if preview.analysis_id:
            analysis = session.scalar(select(Analysis).where(Analysis.id == preview.analysis_id).with_for_update())
        link = valid_magic(session, data.token, lock=True)
        if user.verified_at is None:
            # Neutraliser les accès d’un ancien compte créé sans preuve de propriété.
            user.password_hash = password_hash.hash(secrets.token_urlsafe(48))
            session.execute(delete(UserSession).where(UserSession.user_id == user.id))
        now = datetime.now(timezone.utc)
        user.verified_at = now
        analysis_id = None
        if link.analysis_id:
            if analysis and analysis.user_id is None and analysis.claim_email == email:
                analysis.user_id = user.id
                analysis.guest_hash = None
                analysis_id = analysis.id
            elif analysis and analysis.user_id == user.id:
                analysis_id = analysis.id
        session.execute(update(Analysis).where(
            Analysis.user_id.is_(None), Analysis.claim_email == email
        ).values(user_id=user.id, guest_hash=None))
        session.execute(update(MagicLink).where(
            MagicLink.email == email, MagicLink.used_at.is_(None)
        ).values(used_at=now))
        user_id, email = user.id, user.email
        create_session(session, user_id, request, response)
        return {"id": user_id, "email": email, "analysis_id": analysis_id}
