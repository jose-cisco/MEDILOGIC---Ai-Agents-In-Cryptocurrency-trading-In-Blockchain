from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
import logging
import traceback
import uuid

from app.api.routes import api_router
from app.core.auth import APIKeyMiddleware
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Agent Blockchain Trading",
        description="Multi-agent crypto trading system powered by Ollama GLM-5 with LangGraph, "
        "backtesting, and blockchain integration (Ethereum/Solana)",
        version="1.0.0",
    )
    
    settings = get_settings()
    
    # ─── Security Headers Middleware ─────────────────────────────────────────────
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Force HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Content Security Policy
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' https:; frame-ancestors 'none';"
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissions Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response
    
    # ─── Global Exception Handler ─────────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # Log full error internally with traceback
        error_id = str(uuid.uuid4())
        logger.error(
            "Unhandled exception [%s]: %s\n%s",
            error_id,
            str(exc),
            traceback.format_exc()
        )
        
        # Return generic error to client (no internal details)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred",
                "error_id": error_id,
                "type": "internal_error"
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    # ─── CORS Configuration ───────────────────────────────────────────────────────
    # In production, restrict to specific origins
    cors_origins = ["*"]
    if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS:
        cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # ─── Trusted Host Middleware ─────────────────────────────────────────────────
    # Prevent Host header attacks
    if hasattr(settings, 'ALLOWED_HOSTS') and settings.ALLOWED_HOSTS:
        allowed_hosts = [h.strip() for h in settings.ALLOWED_HOSTS.split(",") if h.strip()]
        if allowed_hosts:
            app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    
    # ─── API Key Authentication Middleware ───────────────────────────────────────
    app.add_middleware(APIKeyMiddleware)
    
    # ─── Routes ───────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    @app.on_event("startup")
    async def validate_environment() -> None:
        # Fail fast on startup for invalid or unsafe production env.
        get_settings().validate_runtime()
        logger.info("Application started successfully - environment validated")

    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring and load balancers."""
        return {"status": "healthy", "version": "1.0.0"}

    return app


app = create_app()
