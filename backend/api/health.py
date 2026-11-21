from datetime import datetime, timezone

from fastapi import APIRouter

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
