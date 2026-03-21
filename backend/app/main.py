"""
FastAPI main application
"""
import sys
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from backend.app.api import auth, query
from backend.app.core.database import init_db
from backend.app.core.rate_limiter import rate_limit_middleware
from backend.app.core.logging_config import setup_logging
from config.settings import settings
import logging

# Setup structured logging
setup_logging(log_level="INFO" if not settings.DEBUG else "DEBUG", log_file="logs/app.log")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart School Information System",
    description="Role-Based AI Agent School Information System with Turkish NLQ",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    return await rate_limit_middleware(request, call_next)

# Include routers
app.include_router(auth.router)
app.include_router(query.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")


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
