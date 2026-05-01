"""
API-Key Authentication & x402 Payment Middleware
==================================================
Layer 1: API-Key validation (when API_KEYS env var is set)
Layer 2: x402 Payment Required protocol (when X402_ENABLED is true)

x402 Payment Exemption:
  Backtesting routes are ALWAYS exempt from x402 payments because
  backtesting is a simulation of cryptocurrency market behavior —
  not real capital deployment. Charging for backtest runs would
  discourage thorough testing and contradict the safety-first principle.

  Exempt routes: /api/v1/backtest/*, /docs, /redoc, /openapi.json, /health, /api/v1/status/*
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.config import get_settings
from app.core.x402 import x402_service, PaymentResource

logger = logging.getLogger(__name__)

# Public paths that never require an API key or x402 payment
_PUBLIC_PREFIXES = ("/docs", "/redoc", "/openapi.json", "/health")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that validates X-API-Key and x402 payments
    on every inbound request.

    Processing order:
    1. Skip public paths (docs, health)
    2. Validate API key (if configured)
    3. Check x402 payment requirement (if enabled)
       - Backtesting routes are ALWAYS exempt from x402
       - Other paid routes require X-Payment header with verified tx_hash
    """

    async def dispatch(self, request: Request, call_next):
        # ── Step 0: Skip public paths ──────────────────────────────────────
        if any(request.url.path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        settings = get_settings()

        # ── Step 1: API Key validation ──────────────────────────────────────
        configured_keys = [k.strip() for k in (settings.API_KEYS or "").split(",") if k.strip()]

        if configured_keys:
            provided = request.headers.get("X-API-Key", "")
            if provided not in configured_keys:
                logger.warning("Rejected request from %s — invalid or missing API key", request.client)
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing X-API-Key header"},
                )

        # ── Step 2: x402 Payment validation ────────────────────────────────
        if getattr(settings, "X402_ENABLED", False):
            x402_result = await _check_x402_payment(request, settings)
            if x402_result is not None:
                return x402_result  # 402 response

        return await call_next(request)


async def _check_x402_payment(request: Request, settings) -> Optional[JSONResponse]:
    """
    Check x402 payment requirement for the request.

    Returns None if the request is allowed (exempt or valid payment).
    Returns a JSONResponse with 402 status if payment is required but missing/invalid.
    """
    path = request.url.path

    # Backtesting is ALWAYS exempt — it's a simulation, not real capital
    if x402_service.is_route_exempt(path):
        return None

    # Determine which resource type this route maps to
    resource = _map_route_to_resource(path, request.method)
    if resource is None:
        # Route doesn't require payment
        return None

    # Check for X-Payment header
    payment_header = request.headers.get("X-Payment", "").strip()

    if not payment_header:
        # No payment provided — return 402 with payment requirements
        payment_response = x402_service.build_402_response(resource)
        if not payment_response:
            # No payment requirement could be built (misconfigured) — allow through
            logger.warning("x402: Could not build payment requirement for %s — allowing request", path)
            return None

        logger.info("x402: Returning 402 for %s (resource: %s)", path, resource.value)
        return JSONResponse(
            status_code=402,
            content=payment_response,
            headers={
                "X-Payment-Required": "true",
                "X-Payment-Resource": resource.value,
            },
        )

    # Verify the payment
    verification = x402_service.verify_payment_header(payment_header, resource)
    if not verification.get("valid", False):
        logger.warning(
            "x402: Invalid payment for %s — %s",
            path, verification.get("reason", "unknown"),
        )
        payment_response = x402_service.build_402_response(resource)
        return JSONResponse(
            status_code=402,
            content={
                **payment_response,
                "payment_error": verification.get("reason", "Payment verification failed"),
            },
            headers={
                "X-Payment-Required": "true",
                "X-Payment-Resource": resource.value,
            },
        )

    # Payment verified — store receipt in request state for downstream use
    receipt = verification.get("receipt")
    if receipt:
        request.state.x402_receipt = receipt
        logger.info(
            "x402: Payment verified for %s — tx_hash=%s amount=$%.6f",
            path, receipt.tx_hash, receipt.amount_usd,
        )

    return None


def _map_route_to_resource(path: str, method: str) -> Optional[PaymentResource]:
    """
    Map an API route to its x402 PaymentResource type.

    Returns None for routes that don't require payment.
    Backtesting routes return None (exempt).
    """

    # Trading execution — requires payment
    if path.startswith("/api/v1/trading/execute"):
        return PaymentResource.TRADE_EXECUTE

    # Market analysis — requires payment
    if path.startswith("/api/v1/trading/analyze"):
        return PaymentResource.TRADE_ANALYZE

    # Enhanced knowledge context — requires payment
    if path.startswith("/api/v1/knowledge/enhanced-context"):
        return PaymentResource.KNOWLEDGE_ENHANCED

    # Hybrid knowledge query — requires payment
    if path.startswith("/api/v1/knowledge/hybrid-query"):
        return PaymentResource.KNOWLEDGE_HYBRID

    # Governance policy check — requires payment
    if path.startswith("/api/v1/governance/policy-check"):
        return PaymentResource.GOVERNANCE_POLICY

    # All other routes (including backtest) — no payment required
    return None