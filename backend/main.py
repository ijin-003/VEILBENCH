from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.health import router as health_router
from backend.api.sessions import router as sessions_router
from backend.config import settings
from backend.services.database import database


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Connect metadata storage without exposing a usable session API if unavailable."""
    await database.start()
    try:
        yield
    finally:
        await database.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Privacy-Preserving Startup Founder Salary Benchmarking System using MPyC",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router, prefix=settings.API_V1_PREFIX, tags=["Health"])
app.include_router(sessions_router, prefix=settings.API_V1_PREFIX, tags=["Sessions"])
# Root health route alias
app.include_router(health_router, tags=["Health"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "description": "Secure Multiparty Computation (SMC) Engine",
        "docs": "/docs"
    }
