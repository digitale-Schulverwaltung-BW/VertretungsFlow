"""
AbsenzFlow - Hauptanwendung
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api import auth, absences, admin

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
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

logger = logging.getLogger(__name__)

# FastAPI App initialisieren
app = FastAPI(
    title="AbsenzFlow API",
    description="API für Abwesenheitsmanagement mit WebUntis-Integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
    content_length = request.headers.get('content-length')

    if content_length:
        try:
            size = int(content_length)
            max_size = 10 * 1024 * 1024  # 10 MB

            if size > max_size:
                logger.warning(f"Request too large: {size} bytes from {request.client.host}")
                return JSONResponse(
                    status_code=413,
                    content={"detail": f"Request too large. Maximum size: {max_size / 1024 / 1024} MB"}
                )
        except ValueError:
            # Invalid Content-Length header
            logger.warning(f"Invalid Content-Length header from {request.client.host}")
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header"}
            )

    return await call_next(request)


# API Routes einbinden
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(absences.router, prefix="/api/absences", tags=["Absences"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "app": "AbsenzFlow",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detaillierter Health Check"""
    return { "status": "ok" }


@app.on_event("startup")
async def startup_event():
    """Wird beim Start der Anwendung ausgeführt"""
    logger.info("🚀 AbsenzFlow Backend gestartet")
    if settings.DEBUG:
        logger.warning("⚠️ DEBUG MODE ENABLED - NOT FOR PRODUCTION!")
    # Ensure critical settings are configured
    if settings.SECRET_KEY == "your-secret-key-change-use-openssl-rand-hex-32":
        raise RuntimeError("Default SECRET_KEY detected! Change before starting.")
    logger.info(f"📝 API Dokumentation: {settings.API_URL}/docs")
    logger.info(f"🔍 Debug Mode: {settings.DEBUG}")
    


@app.on_event("shutdown")
async def shutdown_event():
    """Wird beim Herunterfahren ausgeführt"""
    logger.info("👋 AbsenzFlow Backend gestoppt")
