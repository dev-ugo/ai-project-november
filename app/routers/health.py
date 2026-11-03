"""Application liveness endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Confirm the application responds; this does not check PostgreSQL."""
    return {"status": "ok"}
