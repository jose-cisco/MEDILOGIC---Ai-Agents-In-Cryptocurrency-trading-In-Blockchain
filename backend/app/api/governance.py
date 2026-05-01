"""
Governance API
==============
Exposes agent-governance policy checks, signer management, and dispute
resolution endpoints for the AI-agent trading system.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.governance.agent_governance import governance_service
from app.core.config import get_settings

router = APIRouter()

governance = governance_service


# ── Request / Response schemas ───────────────────────────────────────────────


class PolicyCheckRequest(BaseModel):
    agent_id: str
    action: str
    token_pair: Optional[str] = None
    chain: Optional[str] = None
    risk_score: Optional[float] = None


class PolicyCheckResponse(BaseModel):
    allowed: bool
    reason: str
    policy_version: str


class DisputeRequest(BaseModel):
    agent_id: str
    trade_id: str
    reason: str


class DisputeResponse(BaseModel):
    dispute_id: str
    status: str
    message: str


class SignerUpdateRequest(BaseModel):
    signers: list[str]
    threshold: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/policy-check", response_model=PolicyCheckResponse)
async def policy_check(req: PolicyCheckRequest, http_request: Request):
    """Check whether a proposed agent action complies with governance policy.

    x402: Requires payment when X402_ENABLED=true (X-Payment header).
    """
    settings = get_settings()
    if not settings.ENABLE_AGENT_GOVERNANCE:
        return PolicyCheckResponse(
            allowed=True, reason="Governance disabled", policy_version="none"
        )
    result = governance.pre_trade_check(
        agent_id=req.agent_id,
        token_pair=req.token_pair or "ETH/USDT",
        chain=req.chain or "ethereum",
        max_position_usd=1000.0,
        prompt=req.action,
        semantic_threshold=2,
    )
    return PolicyCheckResponse(
        allowed=result["allowed"],
        reason=" | ".join(result["reasons"]),
        policy_version="v1",
    )


# @router.post("/dispute", response_model=DisputeResponse)
# async def create_dispute(req: DisputeRequest):
#     """Open a dispute for a contested trade decision."""
#     result = governance.open_dispute(
#         agent_id=req.agent_id, trade_id=req.trade_id, reason=req.reason
#     )
#     return DisputeResponse(**result)


@router.get("/status")
async def governance_status():
    """Return current governance configuration and active dispute count."""
    settings = get_settings()
    return {
        "enabled": settings.ENABLE_AGENT_GOVERNANCE,
        "trading_mode": settings.TRADING_MODE,
        "multisig_threshold": settings.GOVERNANCE_MULTISIG_THRESHOLD,
        "active_disputes": 0,
    }


@router.get("/logs")
async def get_governance_logs(limit: int = 50):
    """Return recent agent activity and governance logs."""
    return {"logs": governance.get_activity_logs(limit=limit)}


# @router.put("/signers")
# async def update_signers(req: SignerUpdateRequest):
#     """Update the multisig signer list (requires existing multisig approval)."""
#     settings = get_settings()
#     if not settings.ENABLE_AGENT_GOVERNANCE:
#         raise HTTPException(status_code=400, detail="Governance is disabled")
#     governance.update_signers(signers=req.signers, threshold=req.threshold)
#     return {
#         "status": "updated",
#         "threshold": req.threshold,
#         "signer_count": len(req.signers),
#     }
