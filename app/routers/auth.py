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
from app.models.user import User, UserSession

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
