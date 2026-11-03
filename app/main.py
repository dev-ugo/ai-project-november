"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from app.routers import design_system

from app.routers import health, analyses

app = FastAPI(
    title="CSV Check",
    description="CSV quality reports. Step 1: project scaffold.",
    version="0.1.0",
)
APP_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=APP_DIR / "static"),
    name="static",
)

app.include_router(design_system.router)
app.include_router(health.router)
app.include_router(analyses.router)


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    """Open the API documentation until the web interface is implemented."""
    return RedirectResponse(url="/docs")
