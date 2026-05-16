"""
Identity Verification API
==========================
Endpoints for verifying user identity through LinkedIn or GitHub.
Users MUST complete identity verification before they can trade.

This cuts hackers and threats out of the system by requiring:
  - GitHub account with minimum age and public repos, OR
  - LinkedIn account with verified professional identity

Flow:
  1. GET /api/v1/identity/status — Check current verification status
  2. GET /api/v1/identity/github/auth-url — Get GitHub OAuth redirect URL
  3. POST /api/v1/identity/github/verify — Complete GitHub verification
  4. GET /api/v1/identity/linkedin/auth-url — Get LinkedIn OAuth redirect URL
  5. POST /api/v1/identity/linkedin/verify — Complete LinkedIn verification
  6. GET /api/v1/identity/requirements — Get verification requirements
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional

from app.core.config import get_settings
from app.core.identity_verification import (
    is_user_verified,
    get_user_verification,
    get_user_crypto_priority,
    verify_with_github,
    verify_with_linkedin,
    check_verification_rate_limit,
)
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Request/Response Models ────────────────────────────────────────────────

class GitHubVerifyRequest(BaseModel):
    """GitHub OAuth verification request."""
    code: str = Field(..., description="GitHub OAuth authorization code")
    email: str = Field(..., description="User's email in our system")


class LinkedInVerifyRequest(BaseModel):
    """LinkedIn OAuth verification request."""
    code: str = Field(..., description="LinkedIn OAuth authorization code")
    email: str = Field(..., description="User's email in our system")


class VerificationStatusResponse(BaseModel):
    """Current verification status for a user.
    
    Identity is derived EXCLUSIVELY from GitHub and LinkedIn profiles.
    Users cannot set a custom username or alias.
    """
    email: str
    verified: bool
    provider: Optional[str] = None
    provider_username: Optional[str] = None
    display_name: Optional[str] = None
    verified_at: Optional[str] = None
    reputation_score: Optional[float] = None
    can_trade: bool
    reason: str = ""
    # Crypto experience fields
    crypto_priority: Optional[str] = None  # veteran|experienced|rookie|no_experience|unverified
    crypto_estimated_years: Optional[float] = None
    crypto_can_trade: Optional[bool] = None
    crypto_signals: Optional[list] = None
    dual_verified: Optional[bool] = None
    # Separate provider identities — no custom aliases allowed
    github_username: Optional[str] = None
    linkedin_username: Optional[str] = None
    github_display_name: Optional[str] = None
    linkedin_display_name: Optional[str] = None
    # Cybersecurity beware list screening
    beware_list_clean: Optional[bool] = None
    beware_list_matches: Optional[list] = None


class VerificationRequirementsResponse(BaseModel):
    """Requirements for identity verification."""
    verification_required: bool
    providers: list
    github_requirements: dict
    linkedin_requirements: dict
    message: str


class OAuthURLResponse(BaseModel):
    """OAuth authorization URL for identity provider."""
    url: str
    provider: str
    state: str = ""


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/status", response_model=VerificationStatusResponse)
async def get_verification_status(
    email: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Check identity verification status for a user.
    
    If not verified, the user CANNOT trade — this blocks hackers
    and threats from accessing the trading system.
    """
    settings = get_settings()
    
    # Use the authenticated user's email
    user_email = current_user.get("email", email)
    
    if not settings.IDENTITY_VERIFICATION_REQUIRED:
        return VerificationStatusResponse(
            email=user_email,
            verified=True,
            can_trade=True,
            reason="Identity verification is not required (disabled in config).",
        )
    
    verified = is_user_verified(user_email)
    record = get_user_verification(user_email)
    
    can_trade = verified
    reason = ""
    
    # Get crypto experience data
    crypto_priority = get_user_crypto_priority(user_email) if record else "unverified"
    crypto_estimated_years = record.get("crypto_estimated_years", 0) if record else 0
    crypto_can_trade = record.get("crypto_can_trade", False) if record else False
    crypto_signals = record.get("crypto_signals", []) if record else []
    dual_verified = record.get("dual_verified", False) if record else False
    
    # Get cybersecurity beware list data
    beware_list_clean = record.get("beware_list_clean", True) if record else True
    beware_list_matches = record.get("beware_list_matches", []) if record else []
    
    if not verified:
        if record and not record.get("beware_list_clean", True):
            reason = (
                "IDENTITY BLOCKED: Your identity matches entries on cybersecurity "
                "sanctions/threat lists (e.g., OFAC, Interpol, crypto scam databases). "
                "This is a hard block for platform safety. "
                "Contact support if you believe this is an error."
            )
        else:
            reason = (
                "Identity verification required. Verify via GitHub or LinkedIn "
                "to enable trading. This protects against hackers and malicious actors. "
                "Visit /api/v1/identity/requirements for details."
            )
    elif not crypto_can_trade:
        can_trade = False
        reason = (
            f"Insufficient crypto experience ({crypto_estimated_years:.1f} years estimated, "
            f"priority: {crypto_priority}). Minimum 2 years required. "
            f"Connect both GitHub and LinkedIn for bonus scoring. "
            f"Demonstrate crypto experience through projects, roles, or online presence."
        )
    
    # Mask creator/admin details — never expose internal whitelist info
    provider = record.get("provider") if record else None
    provider_username = record.get("provider_username") if record else None
    display_name = record.get("display_name") if record else None
    github_username = record.get("github_username") if record else None
    linkedin_username = record.get("linkedin_username") if record else None
    github_display_name = record.get("github_display_name") if record else None
    linkedin_display_name = record.get("linkedin_display_name") if record else None
    
    if provider == "creator":
        provider = "verified"
        provider_username = "***"
        display_name = "Verified User"
        github_username = None
        linkedin_username = None
        github_display_name = None
        linkedin_display_name = None
    
    return VerificationStatusResponse(
        email=user_email,
        verified=verified,
        provider=provider,
        provider_username=provider_username,
        display_name=display_name,
        verified_at=record.get("verified_at") if record else None,
        reputation_score=record.get("reputation_score") if record else None,
        can_trade=can_trade,
        reason=reason,
        crypto_priority=crypto_priority,
        crypto_estimated_years=crypto_estimated_years,
        crypto_can_trade=crypto_can_trade,
        crypto_signals=crypto_signals,
        dual_verified=dual_verified,
        # Provider-specific identity — no custom aliases allowed
        github_username=github_username,
        linkedin_username=linkedin_username,
        github_display_name=github_display_name,
        linkedin_display_name=linkedin_display_name,
        # Cybersecurity beware list screening
        beware_list_clean=beware_list_clean,
        beware_list_matches=beware_list_matches if not beware_list_clean else [],
    )


@router.get("/requirements", response_model=VerificationRequirementsResponse)
async def get_verification_requirements():
    """
    Get the requirements for identity verification.
    
    Returns minimum thresholds for GitHub and LinkedIn verification.
    """
    settings = get_settings()
    
    return VerificationRequirementsResponse(
        verification_required=settings.IDENTITY_VERIFICATION_REQUIRED,
        providers=["github", "linkedin"],
        github_requirements={
            "min_account_age_days": settings.IDENTITY_MIN_ACCOUNT_AGE_DAYS,
            "min_public_repos": settings.IDENTITY_MIN_GITHUB_REPOS,
            "description": (
                f"GitHub account must be at least {settings.IDENTITY_MIN_ACCOUNT_AGE_DAYS} days old "
                f"with at least {settings.IDENTITY_MIN_GITHUB_REPOS} public repositories. "
                "This ensures the account belongs to a real developer, not a hacker."
            ),
        },
        linkedin_requirements={
            "min_account_age_days": settings.IDENTITY_MIN_ACCOUNT_AGE_DAYS,
            "min_connections": settings.IDENTITY_MIN_LINKEDIN_CONNECTIONS,
            "description": (
                f"LinkedIn profile must be complete with a verified email "
                f"and at least {settings.IDENTITY_MIN_LINKEDIN_CONNECTIONS} connections. "
                "This ensures the account belongs to a real professional, not a threat actor."
            ),
        },
        message=(
            "Identity verification is MANDATORY for trading. "
            "This protects all users from hackers, scammers, and malicious actors. "
            "Verify through GitHub (developer identity) or LinkedIn (professional identity). "
            "Only ONE provider is required."
        ),
    )


@router.get("/github/auth-url", response_model=OAuthURLResponse)
async def get_github_auth_url():
    """
    Get the GitHub OAuth authorization URL.
    
    Redirect the user to this URL to start GitHub verification.
    After authorization, GitHub returns a code that should be sent
    to POST /api/v1/identity/github/verify.
    """
    settings = get_settings()
    
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.",
        )
    
    import secrets
    state = secrets.token_urlsafe(32)
    
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope=read:user,user:email"
        f"&state={state}"
    )
    
    return OAuthURLResponse(
        url=url,
        provider="github",
        state=state,
    )


@router.post("/github/verify")
async def verify_github_identity(
    request: GitHubVerifyRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Complete GitHub identity verification.
    
    After the user authorizes via GitHub OAuth, the frontend receives
    an authorization code. Send that code here to complete verification.
    
    The system checks:
      - Account age >= minimum days
      - Public repos >= minimum count
      - Profile has a display name
    
    If verification fails, the user CANNOT trade.
    """
    settings = get_settings()
    
    if not settings.IDENTITY_VERIFICATION_REQUIRED:
        return {"verified": True, "message": "Identity verification is not required."}
    
    # Use authenticated user's email
    email = current_user.get("email", request.email)
    
    result = await verify_with_github(request.code, email)
    
    if result.verified:
        can_trade = result.crypto_can_trade
        message = (
            "Identity verified via GitHub! "
            f"Crypto experience: {result.crypto_estimated_years:.1f} years "
            f"(Priority: {result.crypto_priority}). "
        )
        if can_trade:
            message += "You can now trade."
        else:
            message += (
                "However, insufficient crypto experience to trade. "
                "Connect LinkedIn too for bonus scoring, or demonstrate "
                "crypto experience through projects, roles, or online presence."
            )
        return {
            "verified": True,
            "provider": result.provider,
            "provider_username": result.provider_username,
            "display_name": result.display_name,
            "reputation_score": result.reputation_score,
            "verified_at": result.verified_at,
            "can_trade": can_trade,
            "crypto_priority": result.crypto_priority,
            "crypto_estimated_years": result.crypto_estimated_years,
            "crypto_can_trade": result.crypto_can_trade,
            "crypto_signals": result.crypto_signals,
            "dual_verified": result.dual_verified,
            "message": message,
        }
    else:
        return {
            "verified": False,
            "provider": result.provider,
            "failure_reasons": result.failure_reasons,
            "can_trade": False,
            "message": (
                "GitHub verification failed: " + "; ".join(result.failure_reasons)
                + " — You cannot trade until identity is verified."
            ),
        }


@router.get("/linkedin/auth-url", response_model=OAuthURLResponse)
async def get_linkedin_auth_url():
    """
    Get the LinkedIn OAuth authorization URL.
    
    Redirect the user to this URL to start LinkedIn verification.
    After authorization, LinkedIn returns a code that should be sent
    to POST /api/v1/identity/linkedin/verify.
    """
    settings = get_settings()
    
    if not settings.LINKEDIN_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="LinkedIn OAuth is not configured. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET.",
        )
    
    import secrets
    state = secrets.token_urlsafe(32)
    
    url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={settings.LINKEDIN_CLIENT_ID}"
        f"&scope=openid,profile,email"
        f"&state={state}"
    )
    
    return OAuthURLResponse(
        url=url,
        provider="linkedin",
        state=state,
    )


@router.post("/linkedin/verify")
async def verify_linkedin_identity(
    request: LinkedInVerifyRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Complete LinkedIn identity verification.
    
    After the user authorizes via LinkedIn OAuth, the frontend receives
    an authorization code. Send that code here to complete verification.
    
    The system checks:
      - Profile has a verified email
      - Profile has a real name
      - Account appears legitimate
    
    If verification fails, the user CANNOT trade.
    """
    settings = get_settings()
    
    if not settings.IDENTITY_VERIFICATION_REQUIRED:
        return {"verified": True, "message": "Identity verification is not required."}
    
    # Use authenticated user's email
    email = current_user.get("email", request.email)
    
    result = await verify_with_linkedin(request.code, email)
    
    if result.verified:
        can_trade = result.crypto_can_trade
        message = (
            "Identity verified via LinkedIn! "
            f"Crypto experience: {result.crypto_estimated_years:.1f} years "
            f"(Priority: {result.crypto_priority}). "
        )
        if can_trade:
            message += "You can now trade."
        else:
            message += (
                "However, insufficient crypto experience to trade. "
                "Connect GitHub too for bonus scoring, or demonstrate "
                "crypto experience through projects, roles, or online presence."
            )
        return {
            "verified": True,
            "provider": result.provider,
            "provider_username": result.provider_username,
            "display_name": result.display_name,
            "reputation_score": result.reputation_score,
            "verified_at": result.verified_at,
            "can_trade": can_trade,
            "crypto_priority": result.crypto_priority,
            "crypto_estimated_years": result.crypto_estimated_years,
            "crypto_can_trade": result.crypto_can_trade,
            "crypto_signals": result.crypto_signals,
            "dual_verified": result.dual_verified,
            "message": message,
        }
    else:
        return {
            "verified": False,
            "provider": result.provider,
            "failure_reasons": result.failure_reasons,
            "can_trade": False,
            "message": (
                "LinkedIn verification failed: " + "; ".join(result.failure_reasons)
                + " — You cannot trade until identity is verified."
            ),
        }
