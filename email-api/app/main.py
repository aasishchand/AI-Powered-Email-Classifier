"""Faculty Email Classification API - FastAPI application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.middleware.error_handler import error_handler_middleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Ensure CORS origins are never empty when using credentials (browsers reject * with credentials)
_cors_origins = settings.ALLOWED_ORIGINS_LIST or [
    "http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
    "http://127.0.0.1:3000", "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables when using SQLite (local run without Docker)
    from app.db.session import engine
    from app.db.models import Base
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception:
            pass
    # Log that mailbox (and other) routes are loaded
    import sys
    paths = [r.path for r in app.routes if getattr(r, "path", None) and "mailbox" in r.path]
    if paths:
        print("Mailbox API loaded:", ", ".join(sorted(paths)), file=sys.stderr)
    yield
    pass


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise email classification system with ML-powered spam detection and topic modeling",
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.middleware("http")(error_handler_middleware)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


def _cors_headers(origin: str | None) -> dict:
    """Return CORS headers so browser accepts the response even on 500."""
    if origin and origin in _cors_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    return {"Access-Control-Allow-Origin": _cors_origins[0]} if _cors_origins else {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Add CORS headers to HTTPException responses so frontend always sees the error."""
    origin = request.headers.get("origin") or request.headers.get("Origin")
    headers = _cors_headers(origin)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail} if isinstance(exc.detail, str) else {"detail": exc.detail},
        headers=headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Ensure 500 always returns JSON with CORS so the frontend can read the error."""
    logger.exception("Unhandled exception: %s", exc)
    origin = request.headers.get("origin") or request.headers.get("Origin")
    headers = _cors_headers(origin)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)},
        headers=headers,
    )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/")
async def root():
    return {
        "message": settings.APP_NAME,
        "docs_url": "/docs",
        "health_url": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
    )
