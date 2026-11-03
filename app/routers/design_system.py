"""Serve the CSV Check component reference page."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Design system"])
APP_DIR = Path(__file__).resolve().parents[1]


@router.get("/design-system", response_class=HTMLResponse, include_in_schema=False)
def design_system() -> HTMLResponse:
    """Display the reference page with local demonstration data."""
    page = APP_DIR / "templates" / "design-system.html"
    return HTMLResponse(page.read_text(encoding="utf-8"))
