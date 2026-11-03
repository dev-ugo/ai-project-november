"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers import health

app = FastAPI(
    title="CSV Check",
    description="CSV quality reports. Step 1: project scaffold.",
    version="0.1.0",
)

app.include_router(health.router)


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    """Open the API documentation until the web interface is implemented."""
    return RedirectResponse(url="/docs")
