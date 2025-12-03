"""
Medical Scribe AI - Main Application

HIPAA & HITRUST compliant medical scribe solution powered by LLMs.
"""

import os
import uuid
import secrets
import base64
import hashlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
from dotenv import load_dotenv

from src.api.v1 import router as api_v1_router
from src.core.config import get_settings
from src.core.database_init import init_database
from security.audit import initialize_audit_logger

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    settings = get_settings()
    logger.info("Starting Medical Scribe AI",
               environment=settings.APP_ENV,
               version="0.1.0")
    
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    # Initialize audit logging
    storage_url = settings.AZURE_STORAGE_ACCOUNT_URL if settings.AUDIT_LOG_ENABLED else None
    initialize_audit_logger(storage_account_url=storage_url)
    logger.info("Audit logging initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Medical Scribe AI")


# Create FastAPI application
app = FastAPI(
    title="Medical Scribe AI",
    description="HIPAA & HITRUST compliant medical scribe solution powered by LLMs",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True}
)

# Get settings
settings = get_settings()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    nonce = base64.b64encode(secrets.token_bytes(16)).decode('utf-8')
    request.state.csp_nonce = nonce
    
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        # Use 'unsafe-inline' as fallback for browser compatibility with Swagger UI
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; "
            f"script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            f"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            f"img-src 'self' https://fastapi.tiangolo.com https://cdn.jsdelivr.net https://unpkg.com data:; "
            f"font-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            f"connect-src 'self' http://localhost:8000 https://cdn.jsdelivr.net https://unpkg.com; "
            f"frame-ancestors 'none'"
        )
    else:
        # Strict CSP for API endpoints
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
    
    return response


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to all requests"""
    request.state.request_id = str(uuid.uuid4())
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler - prevents information leakage"""
    logger.error("Unhandled exception",
                error=str(exc),
                request_id=getattr(request.state, "request_id", None),
                path=request.url.path)
    
    # Don't expose internal errors in production
    if settings.APP_ENV == "production":
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred"}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)}
        )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    """
    return {
        "status": "healthy",
        "service": "medical-scribe-ai",
        "version": "0.1.0"
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Medical Scribe AI API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


# Include API routers
app.include_router(api_v1_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_config=None  # Use structlog instead
    )
