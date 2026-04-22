import asyncio
from datetime import date, timedelta

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import auth, query, risk
from backend.app.core.database import init_db
from backend.app.core.rate_limiter import rate_limit_middleware
from backend.app.core.logging_config import setup_logging
from config.settings import settings
import logging

setup_logging(log_level="INFO" if not settings.DEBUG else "DEBUG", log_file="logs/app.log")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart School Information System",
    description="Role-Based AI Agent School Information System with Turkish NLQ",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    return await rate_limit_middleware(request, call_next)

app.include_router(auth.router)
app.include_router(query.router)
app.include_router(risk.router)

def _run_ml_scoring_if_stale() -> None:
    """
    ML risk skorlarını arka planda çalıştırır.
    Skorlar eksikse veya 1 günden eskiyse yeniden hesaplar.

    Runs ML risk scoring in a background thread.
    Triggers re-scoring if scores are missing or older than 1 day.
    """
    try:
        from backend.app.core.database import SessionLocal
        from backend.app.models.risk_score import StudentRiskScore

        db = SessionLocal()
        try:
            latest = db.query(StudentRiskScore.computed_at).order_by(
                StudentRiskScore.computed_at.desc()
            ).first()

            if latest and latest[0]:
                age_days = (date.today() - latest[0]).days if hasattr(latest[0], 'year') else 999
                if age_days < 1:
                    score_count = db.query(StudentRiskScore).count()
                    logger.info(
                        f"ML risk scores are fresh ({score_count} records, {age_days}d old). "
                        "Skipping re-scoring."
                    )
                    return
        finally:
            db.close()

        logger.info("ML risk scores missing or stale → running scoring pipeline …")
        from database.score_students_ml import main as run_scoring
        run_scoring()
        logger.info("ML risk scoring complete.")

    except Exception as exc:
        logger.warning(f"ML scoring skipped (non-fatal): {exc}")

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup, then trigger ML scoring in background."""
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_ml_scoring_if_stale)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Smart School Information System API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
