"""CSV upload and analysis endpoints."""

import csv
from typing import Literal

from fastapi import APIRouter, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import engine
from app.models.analysis import Analysis
from app.services.csv_analyzer import analyze_csv

router = APIRouter(prefix="/analyses", tags=["Analyses"])

MAX_FILE_SIZE = 1024 * 1024


@router.post("", status_code=201)
def create_analysis(
    file: UploadFile,
    delimiter: Literal[",", ";"] = ",",
) -> dict:
    """Analyze a CSV file and save its report."""
    filename = (file.filename or "").strip()

    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file.")

    if len(filename) > 255:
        raise HTTPException(status_code=400, detail="Filename is too long.")

    content = file.file.read(MAX_FILE_SIZE + 1)

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Maximum file size is 1 MiB.",
        )

    if b"\x00" in content:
        raise HTTPException(
            status_code=400,
            detail="CSV contains null bytes.",
        )

    try:
        report = analyze_csv(content, delimiter=delimiter)
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail="The CSV file must use UTF-8 encoding.",
        ) from error
    except (ValueError, csv.Error) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    with Session(engine) as session:
        analysis = Analysis(filename=filename, **report)
        session.add(analysis)
        session.commit()
        session.refresh(analysis)

        return {
            "id": analysis.id,
            "filename": analysis.filename,
            "created_at": analysis.created_at,
            **report,
        }