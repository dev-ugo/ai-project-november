"""Analyse des CSV, historique privé et demande d’envoi du fichier corrigé."""
import csv
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (ensure_guest, get_current_user, get_optional_user, guest_digest, rate_limit, require_csrf)
from app.database import engine
from app.models.analysis import Analysis
from app.models.user import User
from app.services.csv_analyzer import analyze_csv
from app.services.csv_corrector import correct_csv
from app.services.email_sender import (
    EmailConfigurationError, EmailDeliveryError,
    ensure_email_configured, send_corrected_csv,
)

router = APIRouter(prefix="/analyses", tags=["Analyses"])
MAX_FILE_SIZE = 1024 * 1024


def serialize_analysis(analysis: Analysis, *, detailed: bool = False) -> dict:
    report = {
        "id": analysis.id,
        "filename": analysis.filename,
        "created_at": analysis.created_at,
        "row_count": analysis.row_count,
        "duplicate_count": analysis.duplicate_count,
        "empty_cell_count": analysis.empty_cell_count,
        "correction_available": analysis.correction_key is not None,
        "email_sent_at": analysis.email_sent_at,
    }
    if detailed:
        report["anomalies"] = analysis.anomalies
    return report


@router.post("", status_code=201, dependencies=[Depends(require_csrf)])
def create_analysis(
    file: UploadFile,
    request: Request,
    response: Response,
    delimiter: Literal[",", ";"] = ",",
    user: User | None = Depends(get_optional_user),
) -> dict:
    """Analyser un CSV et lier son rapport au compte connecté."""
    if user is None:
        rate_limit(f"upload-ip:{request.client.host if request.client else 'unknown'}", 20, 3600)
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".csv"):
        raise HTTPException(400, "Upload a CSV file.")
    if len(filename) > 255:
        raise HTTPException(400, "Filename is too long.")
    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Maximum file size is 1 MiB.")
    if b"\x00" in content:
        raise HTTPException(400, "CSV contains null bytes.")
    try:
        report = analyze_csv(content, delimiter=delimiter)
        corrected = correct_csv(content, delimiter=delimiter)
    except UnicodeDecodeError as error:
        raise HTTPException(400, "The CSV file must use UTF-8 encoding.") from error
    except (ValueError, csv.Error) as error:
        raise HTTPException(400, str(error)) from error
    with Session(engine) as session:
        analysis = Analysis(filename=filename, user_id=user.id if user else None,
                            guest_hash=ensure_guest(request, response) if not user else None,
                            corrected_csv=corrected, **report)
        session.add(analysis)
        session.commit()
        session.refresh(analysis)
        return serialize_analysis(analysis, detailed=True)


@router.get("")
def list_analyses(user: User = Depends(get_current_user)) -> list[dict]:
    """Lister les 50 derniers rapports du compte connecté uniquement."""
    with Session(engine) as session:
        analyses = session.scalars(
            select(Analysis).where(Analysis.user_id == user.id)
            .order_by(Analysis.created_at.desc(), Analysis.id.desc()).limit(50)
        ).all()
        return [serialize_analysis(analysis) for analysis in analyses]


def owned_analysis(session: Session, analysis_id: int, request: Request, user: User | None, *, lock=False) -> Analysis:
    statement = select(Analysis).where(Analysis.id == analysis_id)
    if lock:
        statement = statement.with_for_update()
    analysis = session.scalar(statement)
    allowed = analysis is not None and (
        (user is not None and analysis.user_id == user.id)
        or (analysis.user_id is None and analysis.guest_hash is not None
            and analysis.guest_hash == guest_digest(request))
    )
    if not allowed:
        raise HTTPException(404, "Analyse introuvable.")
    return analysis


@router.get("/{analysis_id}")
def get_analysis(analysis_id: int, request: Request, user: User | None = Depends(get_optional_user)) -> dict:
    """Accès par propriétaire connecté ou cookie secret du navigateur invité."""
    with Session(engine) as session:
        return serialize_analysis(owned_analysis(session, analysis_id, request, user), detailed=True)


from pydantic import BaseModel, EmailStr, Field


class EmailRequest(BaseModel):
    email: EmailStr | None = Field(default=None, max_length=254)


def email_guest(session: Session, analysis_id: int, request: Request, data: EmailRequest | None, user: User | None) -> dict:
    from app.services.magic_links import issue_link
    rate_limit(f"magic-ip:{request.client.host if request.client else 'unknown'}", 20, 3600)
    analysis = owned_analysis(session, analysis_id, request, user, lock=True)
    if not analysis.corrected_csv:
        raise HTTPException(409, "Réimportez ce fichier pour préparer sa correction.")
    if data is None or data.email is None:
        raise HTTPException(422, "Indiquez votre adresse e-mail pour recevoir la correction.")
    email = str(data.email).lower()
    try:
        ensure_email_configured()
        analysis.claim_email = email
        issue_link(session, email, analysis)
    except EmailConfigurationError as error:
        raise HTTPException(503, str(error)) from error
    except EmailDeliveryError as error:
        raise HTTPException(502, str(error)) from error
    analysis.email_sent_at = datetime.now(timezone.utc)
    sent_at = analysis.email_sent_at
    session.commit()
    return {"message": "Version corrigée envoyée. Confirmez votre adresse depuis l’e-mail pour créer votre espace et retrouver ce rapport.",
            "email_sent_at": sent_at, "confirmation_required": True}


@router.post("/{analysis_id}/email", dependencies=[Depends(require_csrf)])
def email_analysis(analysis_id: int, request: Request, data: EmailRequest | None = None,
                   user: User | None = Depends(get_optional_user)) -> dict:
    """Envoyer une fois le fichier corrigé à l’adresse du compte connecté."""
    with Session(engine) as session:
        if user is None or (session.get(Analysis, analysis_id) is not None
                            and session.get(Analysis, analysis_id).user_id is None):
            return email_guest(session, analysis_id, request, data, user)
        # Verrouiller le compte sérialise ses envois, y compris depuis plusieurs onglets.
        owner = session.scalar(select(User).where(User.id == user.id).with_for_update())
        analysis = session.scalar(select(Analysis).where(
            Analysis.id == analysis_id, Analysis.user_id == user.id,
        ).with_for_update())
        if analysis is None:
            raise HTTPException(404, "Analyse introuvable.")
        if analysis.email_sent_at:
            return {"message": "Ce fichier a déjà été transmis au service d’e-mail.", "email_sent_at": analysis.email_sent_at}
        if not analysis.corrected_csv or not analysis.correction_key:
            raise HTTPException(409, "Réimportez ce fichier pour préparer sa correction.")
        try:
            ensure_email_configured()
        except EmailConfigurationError as error:
            raise HTTPException(503, str(error)) from error
        now = datetime.now(timezone.utc)
        window = owner.email_window_at
        if window is not None and window.tzinfo is None:
            window = window.replace(tzinfo=timezone.utc)
        if window is None or window <= now - timedelta(hours=1):
            owner.email_window_at = now
            owner.email_attempts = 0
        if owner.email_attempts >= 5:
            raise HTTPException(429, "Limite de cinq demandes d’e-mail par heure atteinte.")
        owner.email_attempts += 1
        try:
            send_corrected_csv(analysis, owner.email)
        except EmailDeliveryError as error:
            session.commit()  # Une tentative en échec compte aussi dans la limite.
            raise HTTPException(502, str(error)) from error
        analysis.email_sent_at = datetime.now(timezone.utc)
        sent_at = analysis.email_sent_at
        session.commit()
        return {"message": "Fichier transmis au service d’e-mail. Vérifiez aussi vos indésirables.", "email_sent_at": sent_at}
