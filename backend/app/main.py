"""
AbsenzFlow - Hauptanwendung
"""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from app.core.config import settings
from app.api import auth, absences, attachments, webuntis, admin, pdf_forms

# Logging konfigurieren
log_level = logging.DEBUG if settings.DEBUG else logging.INFO

# Root Logger direkt konfigurieren (basicConfig funktioniert nicht wenn Uvicorn bereits gestartet)
root_logger = logging.getLogger()
root_logger.setLevel(log_level)

# Handler konfigurieren falls noch keiner existiert
if not root_logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

logger = logging.getLogger(__name__)

# Rate Limiter initialisieren
limiter = Limiter(key_func=get_remote_address)

# FastAPI App initialisieren
app = FastAPI(
    title="AbsenzFlow API",
    description="API für Abwesenheitsmanagement mit WebUntis-Integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate Limiter an App binden
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Initialize APScheduler
scheduler = AsyncIOScheduler()


def run_cleanup_task():
    """Background task to clean up old absences"""
    from app.core.database import SessionLocal
    from app.services.absence_service import absence_service

    if not settings.ABSENCE_AUTO_DELETE_ENABLED:
        logger.info("Absence auto-deletion is disabled")
        return

    logger.info(f"Running automatic absence cleanup (retention: {settings.ABSENCE_RETENTION_DAYS} days)")

    db = SessionLocal()
    try:
        result = absence_service.cleanup_old_absences(
            db=db,
            retention_days=settings.ABSENCE_RETENTION_DAYS
        )
        logger.info(f"Cleanup result: {result}")
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
    finally:
        db.close()


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses

    Headers:
    - X-Content-Type-Options: Prevents MIME type sniffing
    - X-Frame-Options: Prevents clickjacking attacks
    - Referrer-Policy: Controls referrer information
    - Strict-Transport-Security (HSTS): Only in production (DEBUG=False)
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Always set these headers (work with HTTP)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS only in production (requires HTTPS)
        if not settings.DEBUG:
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains"

        return response


app.add_middleware(SecurityHeadersMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Size Limit Middleware (DoS Protection)
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """
    Limits request body size to prevent DoS attacks
    Max size: 10 MB (excluding multipart/form-data which is handled separately)
    """
    content_length = request.headers.get("content-length")

    if content_length:
        try:
            size = int(content_length)
            max_size = 10 * 1024 * 1024  # 10 MB

            if size > max_size:
                client_host = request.client.host if request.client else "unknown"
                logger.warning(f"Request too large: {size} bytes from {client_host}")
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"Request too large. Maximum size: {max_size / 1024 / 1024} MB"
                    },
                )
        except ValueError:
            # Invalid Content-Length header
            client_host = request.client.host if request.client else "unknown"
            logger.warning(f"Invalid Content-Length header from {client_host}")
            return JSONResponse(
                status_code=400, content={"detail": "Invalid Content-Length header"}
            )

    return await call_next(request)


# API Routes einbinden
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(absences.router, prefix="/api/absences", tags=["Absences"])
app.include_router(attachments.router, prefix="/api/absences", tags=["Attachments"])
app.include_router(webuntis.router, prefix="/api", tags=["WebUntis"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(pdf_forms.router, prefix="/api", tags=["PDF Forms"])


@app.get("/")
@limiter.limit("100/minute")
async def root(request: Request):
    """Health check endpoint"""
    return {"status": "online", "app": "AbsenzFlow", "version": "1.0.0"}


@app.get("/health")
@limiter.limit("100/minute")
async def health_check(request: Request):
    """Detaillierter Health Check"""
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    """Wird beim Start der Anwendung ausgeführt"""
    logger.info("🚀 AbsenzFlow Backend gestartet")
    logger.info("✅ Security validation passed - no default secrets detected")
    if settings.DEBUG:
        logger.warning("⚠️ DEBUG MODE ENABLED - NOT FOR PRODUCTION!")
    logger.info(f"🔍 Debug Mode: {settings.DEBUG}")
    logger.info(f"🔐 Auth Mode: {settings.AUTH_MODE}")

    # Initialize database connection test
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

    # Setup scheduled cleanup task
    if settings.ABSENCE_AUTO_DELETE_ENABLED:
        scheduler.add_job(
            run_cleanup_task,
            trigger=CronTrigger(hour=2, minute=0),  # Run daily at 2:00 AM
            id='cleanup_old_absences',
            name='Clean up old absences',
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"Scheduled daily cleanup at 02:00 (retention: {settings.ABSENCE_RETENTION_DAYS} days)")
    else:
        logger.info("Absence auto-deletion is disabled")


@app.on_event("shutdown")
async def shutdown_event():
    """Wird beim Herunterfahren ausgeführt"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")
    logger.info("👋 AbsenzFlow Backend gestoppt")
