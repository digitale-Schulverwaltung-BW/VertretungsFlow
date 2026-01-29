"""
AbsenzFlow - Hauptanwendung
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    return {
        "status": "healthy",
        "database": "connected",  # TODO: Tatsächlichen DB-Status prüfen
        "ldap": "configured"      # TODO: LDAP-Verbindung prüfen
    }


@app.on_event("startup")
async def startup_event():
    """Wird beim Start der Anwendung ausgeführt"""
    logger.info("🚀 AbsenzFlow Backend gestartet")
    logger.info(f"📝 API Dokumentation: {settings.API_URL}/docs")
    logger.info(f"🔍 Debug Mode: {settings.DEBUG}")


@app.on_event("shutdown")
async def shutdown_event():
    """Wird beim Herunterfahren ausgeführt"""
    logger.info("👋 AbsenzFlow Backend gestoppt")
