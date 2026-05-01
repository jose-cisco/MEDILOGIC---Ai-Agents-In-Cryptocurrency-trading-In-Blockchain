"""
x402 Payment API
================
Exposes x402 payment protocol information, pricing, and verification endpoints.

Backtesting is ALWAYS exempt from x402 payments — see /payments/exempt-routes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import logging
from app.core.x402 import (
    x402_service,
    get_resource_price,
    PaymentResource,
    X402_EXEMPT_PREFIXES,
)
from app.core.config import get_settings

router = APIRouter()


class PaymentVerifyRequest(BaseModel):
    """Client submits a payment for verification."""
    tx_hash: str
    network_id: str = ""
    from_address: str = ""
    resource: str  # e.g. "trade_execute"


class PaymentVerifyResponse(BaseModel):
    valid: bool
    reason: str
    tx_hash: Optional[str] = None
    amount_usd: Optional[float] = None
    resource: Optional[str] = None


@router.get("/status")
async def payment_status():
    """Current x402 payment protocol configuration and pricing."""
    settings = get_settings()
    pricing = {}
    for resource in PaymentResource:
        pricing[resource.value] = get_resource_price(resource)

    return {
        "enabled": x402_service.enabled,
        "testnet": x402_service.testnet,
        "chain_id": settings.X402_CHAIN_ID,
        "usdc_address": settings.X402_USDC_ADDRESS,
        "recipient_configured": bool(settings.X402_RECIPIENT_ADDRESS),
        "recipient_address": settings.X402_RECIPIENT_ADDRESS if x402_service.enabled else None,
        "pricing_usd": pricing,
        "protocol_version": 1,
    }


@router.get("/exempt-routes")
async def exempt_routes():
    """
    List routes exempt from x402 payment requirements.

    Backtesting is ALWAYS exempt because it simulates cryptocurrency
    market behavior without real capital deployment.
    """
    return {
        "exempt_prefixes": list(X402_EXEMPT_PREFIXES),
        "reason": (
            "Backtesting is a simulation of crypto market behavior — not real capital "
            "deployment. Charging for backtest runs would discourage thorough testing "
            "and contradict the safety-first principle of simulating before trading."
        ),
        "details": [
            {
                "prefix": prefix,
                "reason": "Simulation endpoint — no real capital at risk",
            }
            for prefix in X402_EXEMPT_PREFIXES
            if "backtest" in prefix
        ],
    }


@router.post("/verify", response_model=PaymentVerifyResponse)
async def verify_payment(request: PaymentVerifyRequest):
    """
    Verify an on-chain payment for a given resource.

    This endpoint allows clients to pre-verify a payment before
    making a paid API call. The middleware also verifies on each
    paid request, but this endpoint is useful for debugging.
    """
    if not x402_service.enabled:
        return PaymentVerifyResponse(
            valid=True, reason="x402 payment protocol is not enabled"
        )

    # Map resource string to enum
    resource_map = {r.value: r for r in PaymentResource}
    resource_enum = resource_map.get(request.resource)
    if resource_enum is None:
        return PaymentVerifyResponse(
            valid=False,
            reason=f"Unknown resource: {request.resource}. Valid: {list(resource_map.keys())}",
        )

    import json
    payment_header = json.dumps({
        "tx_hash": request.tx_hash,
        "network_id": request.network_id,
        "from_address": request.from_address,
    })

    result = x402_service.verify_payment_header(payment_header, resource_enum)

    receipt = result.get("receipt")
    return PaymentVerifyResponse(
        valid=result.get("valid", False),
        reason=result.get("reason", "unknown"),
        tx_hash=receipt.tx_hash if receipt else None,
        amount_usd=receipt.amount_usd if receipt else None,
        resource=receipt.resource if receipt else request.resource,
    )


@router.get("/requirement/{resource}")
async def get_payment_requirement(resource: str):
    """
    Get the payment requirement for a specific resource.

    Returns the 402 response body that would be sent for an unpaid request,
    allowing clients to prepare payment before making the actual API call.
    """
    resource_map = {r.value: r for r in PaymentResource}
    resource_enum = resource_map.get(resource)
    if resource_enum is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown resource: {resource}. Valid: {list(resource_map.keys())}",
        )

    if not x402_service.enabled:
        return {
            "payment_required": False,
            "reason": "x402 payment protocol is not enabled",
        }

    requirement = x402_service.build_402_response(resource_enum)
    return requirement


@router.get("/providers/claw402")
async def claw402_provider_info():
    """
    Claw402 built-in x402 provider catalogue.
    No account, no API key — wallet pays per request on Base.
    """
    from app.core.llm import CLAW402_MODELS
    settings = get_settings()

    wallet_address = None
    wallet_configured = bool(settings.CLAW402_WALLET_PRIVATE_KEY)
    if wallet_configured:
        try:
            from app.core.claw402_transport import _get_wallet_address
            wallet_address = _get_wallet_address()
        except Exception:
            pass

    # Group by provider label
    by_provider: dict[str, list] = {}
    for model_id, meta in CLAW402_MODELS.items():
        p = meta["provider"]
        by_provider.setdefault(p, []).append({
            "model_id": model_id,
            "label": meta["label"],
        })

    return {
        "provider": "Claw402",
        "chain": "Base",
        "chain_id": 8453,
        "base_url": settings.CLAW402_BASE_URL,
        "payment_method": "x402 — USDC on Base per request",
        "no_api_key_required": True,
        "wallet_configured": wallet_configured,
        "wallet_address": wallet_address,
        "total_models": len(CLAW402_MODELS),
        "models_by_provider": by_provider,
        "all_model_ids": list(CLAW402_MODELS.keys()),
        "docs": "https://claw402.com",
    }


@router.get("/providers/openrouter")
async def openrouter_provider_info():
    """
    OpenRouter provider catalogue.
    Requires OPENROUTER_API_KEY.
    Fetches LIVE pricing and provider information from OpenRouter.
    """
    from app.core.llm import OPENROUTER_MODELS
    settings = get_settings()
    
    # Try to fetch live data if key is present
    live_models = []
    if settings.OPENROUTER_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    live_models = data.get("data", [])
        except Exception as e:
            logging.error("Failed to fetch live OpenRouter models: %s", e)

    # Merge live data with our local enforcement list
    merged_models = []
    
    # 1. Add our hardcoded/enforced models with live pricing if available
    for mid, meta in OPENROUTER_MODELS.items():
        model_info = {
            "id": mid,
            "label": meta["label"],
            "reasoning_enforced": meta.get("reasoning", False),
            "pricing": None,
            "description": "",
            "is_enforced": True,
        }
        live_match = next((m for m in live_models if m.get("id") == mid), None)
        if live_match:
            model_info["pricing"] = live_match.get("pricing")
            model_info["description"] = live_match.get("description", "")
        merged_models.append(model_info)

    # 2. Add other variations of minimax, glm, grok found in the live feed
    # This captures "many providers in different price" as requested.
    interest_keywords = ["minimax", "glm-5", "grok-4"]
    for m in live_models:
        mid = m.get("id", "").lower()
        # Skip if already in merged_models
        if any(sm["id"] == m.get("id") for sm in merged_models):
            continue
            
        # Only allow variations of our core circles
        if any(kw in mid for kw in interest_keywords):
            model_info = {
                "id": m.get("id"),
                "label": m.get("name", m.get("id")),
                "reasoning_enforced": False, 
                "pricing": m.get("pricing"),
                "description": m.get("description", ""),
                "is_enforced": False,
            }
            merged_models.append(model_info)
    return {
        "provider": "OpenRouter",
        "configured": bool(settings.OPENROUTER_API_KEY),
        "base_url": settings.OPENROUTER_BASE_URL,
        "models": merged_models,
        "total_models": len(merged_models),
        "docs": "https://openrouter.ai/docs",
        "live_fetch_success": bool(live_models),
    }