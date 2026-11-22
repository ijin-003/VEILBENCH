from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from backend.config import settings
from backend.services.database import database

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint returning system status, timestamp, and runtime environment.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "session_storage": "available" if database.available else "unavailable",
        "mpc_configuration": {
            "parties": settings.MPC_PARTIES_COUNT,
            "threshold": settings.MPC_THRESHOLD,
            "honest_majority": settings.MPC_PARTIES_COUNT > 2 * settings.MPC_THRESHOLD
        }
    }


@router.get("/health/live")
async def liveness_check():
    """Liveness only: the process is running and can accept requests."""
    return {"status": "alive", "service": settings.PROJECT_NAME}


@router.get("/health/ready")
async def readiness_check():
    """Readiness: metadata storage must be connected before traffic is served."""
    if not database.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session storage is not ready",
        )
    return {
        "status": "ready",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "session_storage": "available",
    }
