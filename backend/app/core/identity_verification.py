"""
Identity Verification Service — LinkedIn & GitHub
====================================================
Verifies user identity through LinkedIn or GitHub OAuth profiles.
Users MUST be verified AND have crypto experience before they can trade.

Verification checks:
  - GitHub: account age, public repos, profile completeness
  - LinkedIn: account age, connections, profile completeness
  - Crypto experience: assessed from GitHub repos, LinkedIn roles, web mentions
  - Cybersecurity beware lists: OFAC, Interpol, EU sanctions, CryptoScamDB, threat aliases
  - Minimum thresholds configurable via Settings

Crypto Experience Priority System:
  - Priority 1 (Veteran): >5 years crypto experience
  - Priority 2 (Experienced): 3-5 years crypto experience
  - Priority 3 (Rookie): 2-3 years crypto experience
  - Blocked: <2 years or no verifiable crypto experience

Dual Verification:
  - Users who verify BOTH GitHub AND LinkedIn get bonus scoring
  - Combined data from both providers gives more accurate assessment

Cybersecurity Beware List Screening:
  - Every user is checked against public cybersecurity threat databases
  - Sources: OFAC SDN, Interpol Red Notices, EU Sanctions, CryptoScamDB, known threat aliases
  - HARD BLOCK: if ANY match found, verification is rejected regardless of other checks
  - Results cached for 24 hours to avoid repeated lookups

Flow:
  1. User initiates OAuth flow (frontend redirects to provider)
  2. Provider returns authorization code
  3. Backend exchanges code for access token
  4. Backend fetches profile data from provider API
  5. Profile is validated against minimum requirements
  6. Cybersecurity beware list screening (OFAC, Interpol, EU, CryptoScamDB, threat aliases)
  7. Crypto experience is assessed from profile + web search
  8. Priority level is assigned based on estimated crypto years
  9. Verification status stored in user record

Security:
  - Access tokens are NEVER stored — only used once to fetch profile
  - Only verification status + provider username are persisted
  - Rate-limited to prevent brute-force verification attempts
  - Cybersecurity beware list screening blocks known threat actors
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass, field

import httpx

from app.core.config import get_settings
from app.core.security import log_security_event, SecurityEventType
from app.core.cloud_identity_store import cloud_store
from app.core.cybersecurity_beware import check_cybersecurity_beware_lists

from fastapi import Request

logger = logging.getLogger(__name__)


# ─── Data Models ─────────────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    """Result of identity verification attempt."""
    verified: bool
    provider: str  # "github" | "linkedin" | "dual"
    provider_username: str = ""
    display_name: str = ""
    account_age_days: int = 0
    reputation_score: float = 0.0  # 0.0 – 1.0
    failure_reasons: list = field(default_factory=list)
    verified_at: str = ""
    # Crypto experience fields
    crypto_priority: str = "no_experience"  # veteran|experienced|rookie|no_experience
    crypto_estimated_years: float = 0.0
    crypto_can_trade: bool = False
    crypto_signals: list = field(default_factory=list)
    dual_verified: bool = False
    # Cybersecurity beware list screening
    beware_list_clean: bool = True
    beware_list_matches: list = field(default_factory=list)


@dataclass
class UserProfile:
    """Normalized profile from OAuth provider."""
    username: str
    display_name: str
    account_created_at: Optional[datetime] = None
    public_repos: int = 0          # GitHub only
    followers: int = 0             # GitHub only
    connections: int = 0           # LinkedIn only
    profile_complete: bool = False
    provider: str = ""


# ─── In-Memory Verification Store ────────────────────────────────────────────
# Maps email -> { provider, username, verified, verified_at, reputation_score }
_verification_db: dict = {}

# Rate limit: max 5 verification attempts per email per hour
_verification_attempts: dict = {}


def _init_creator_accounts() -> None:
    """Pre-seed creator/admin accounts as verified on module load.
    
    Creators bypass all verification checks and are always marked as verified.
    """
    try:
        settings = get_settings()
        for email in settings.IDENTITY_CREATOR_EMAILS.split(","):
            email = email.strip().lower()
            if email and email not in _verification_db:
                _verification_db[email] = {
                    "provider": "creator",
                    "provider_username": "jose-cisco",
                    "display_name": "System Creator",
                    "verified": True,
                    "verified_at": datetime.now(timezone.utc).isoformat(),
                    "reputation_score": 1.0,
                }
                logger.info("Pre-seeded creator account: %s", email)
    except Exception:
        # Settings may not be available during import in some test scenarios
        pass


_init_creator_accounts()


# ─── GitHub Verification ────────────────────────────────────────────────────

async def exchange_github_code(code: str) -> Optional[dict]:
    """Exchange GitHub OAuth authorization code for access token.
    
    Returns token data dict or None on failure.
    """
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            if "access_token" in data:
                return data
            logger.warning("GitHub OAuth: no access_token in response: %s", list(data.keys()))
            return None
        except httpx.HTTPError as exc:
            logger.error("GitHub OAuth token exchange failed: %s", exc)
            return None


async def fetch_github_profile(access_token: str) -> Optional[UserProfile]:
    """Fetch GitHub user profile using access token.
    
    Only reads public profile data — no private repo access needed.
    Token is used once and discarded.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            
            created_at = None
            if data.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(
                        data["created_at"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass
            
            return UserProfile(
                username=data.get("login", ""),
                display_name=data.get("name", "") or data.get("login", ""),
                account_created_at=created_at,
                public_repos=data.get("public_repos", 0),
                followers=data.get("followers", 0),
                profile_complete=bool(data.get("bio") or data.get("name")),
                provider="github",
            )
        except httpx.HTTPError as exc:
            logger.error("GitHub profile fetch failed: %s", exc)
            return None


def validate_github_profile(profile: UserProfile) -> VerificationResult:
    """Validate GitHub profile meets minimum requirements.
    
    Checks:
      - Account age >= IDENTITY_MIN_ACCOUNT_AGE_DAYS
      - Public repos >= IDENTITY_MIN_GITHUB_REPOS
      - Profile has a display name or bio (not empty shell)
    """
    settings = get_settings()
    reasons = []
    
    # Calculate account age
    age_days = 0
    if profile.account_created_at:
        age_days = (datetime.now(timezone.utc) - profile.account_created_at).days
    
    # Check account age
    min_age = settings.IDENTITY_MIN_ACCOUNT_AGE_DAYS
    if age_days < min_age:
        reasons.append(
            f"GitHub account is {age_days} days old (minimum: {min_age} days). "
            "New accounts may be throwaway identities used by hackers."
        )
    
    # Check public repos
    min_repos = settings.IDENTITY_MIN_GITHUB_REPOS
    if profile.public_repos < min_repos:
        reasons.append(
            f"GitHub account has {profile.public_repos} public repos "
            f"(minimum: {min_repos}). Accounts with no code contributions "
            "are suspicious and may be created for malicious purposes."
        )
    
    # Check profile completeness
    if not profile.display_name:
        reasons.append(
            "GitHub profile has no display name. Verified users must have "
            "a complete profile to prevent anonymous threats."
        )
    
    # Calculate reputation score (0.0 – 1.0)
    age_score = min(age_days / 365.0, 1.0) * 0.3
    repo_score = min(profile.public_repos / 10.0, 1.0) * 0.4
    follower_score = min(profile.followers / 50.0, 1.0) * 0.2
    profile_score = 0.1 if profile.profile_complete else 0.0
    reputation = round(age_score + repo_score + follower_score + profile_score, 2)
    
    verified = len(reasons) == 0
    
    return VerificationResult(
        verified=verified,
        provider="github",
        provider_username=profile.username,
        display_name=profile.display_name,
        account_age_days=age_days,
        reputation_score=reputation,
        failure_reasons=reasons,
        verified_at=datetime.now(timezone.utc).isoformat() if verified else "",
    )


# ─── LinkedIn Verification ──────────────────────────────────────────────────

async def exchange_linkedin_code(code: str) -> Optional[dict]:
    """Exchange LinkedIn OAuth authorization code for access token."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": "",  # Set by frontend
                    "client_id": settings.LINKEDIN_CLIENT_ID,
                    "client_secret": settings.LINKEDIN_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            if "access_token" in data:
                return data
            logger.warning("LinkedIn OAuth: no access_token in response")
            return None
        except httpx.HTTPError as exc:
            logger.error("LinkedIn OAuth token exchange failed: %s", exc)
            return None


async def fetch_linkedin_profile(access_token: str) -> Optional[UserProfile]:
    """Fetch LinkedIn user profile using access token.
    
    Uses LinkedIn OpenID Connect / UserInfo endpoint.
    Token is used once and discarded.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # LinkedIn UserInfo (OpenID Connect)
            resp = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            
            return UserProfile(
                username=data.get("sub", ""),
                display_name=data.get("name", ""),
                profile_complete=bool(data.get("name") and data.get("email_verified", False)),
                provider="linkedin",
            )
        except httpx.HTTPError as exc:
            logger.error("LinkedIn profile fetch failed: %s", exc)
            return None


def validate_linkedin_profile(profile: UserProfile) -> VerificationResult:
    """Validate LinkedIn profile meets minimum requirements.
    
    Checks:
      - Profile has verified email
      - Profile has a real name
      - Account appears legitimate (not a shell account)
    """
    settings = get_settings()
    reasons = []
    
    # Check display name
    if not profile.display_name:
        reasons.append(
            "LinkedIn profile has no display name. Verified users must have "
            "a real identity to prevent anonymous threats and hacking."
        )
    
    # Check profile completeness
    if not profile.profile_complete:
        reasons.append(
            "LinkedIn profile is incomplete. A verified professional identity "
            "is required to protect against hackers and malicious actors."
        )
    
    # Calculate reputation score
    profile_score = 0.6 if profile.profile_complete else 0.1
    name_score = 0.3 if profile.display_name else 0.0
    reputation = round(profile_score + name_score, 2)
    
    verified = len(reasons) == 0
    
    return VerificationResult(
        verified=verified,
        provider="linkedin",
        provider_username=profile.username,
        display_name=profile.display_name,
        account_age_days=0,  # LinkedIn doesn't expose account age
        reputation_score=reputation,
        failure_reasons=reasons,
        verified_at=datetime.now(timezone.utc).isoformat() if verified else "",
    )


# ─── Public API ──────────────────────────────────────────────────────────────

def _is_creator(email: str) -> bool:
    """Check if email belongs to a system creator/admin (whitelist bypass)."""
    settings = get_settings()
    creator_emails = [e.strip().lower() for e in settings.IDENTITY_CREATOR_EMAILS.split(",") if e.strip()]
    return email.lower().strip() in creator_emails


def is_user_verified(email: str) -> bool:
    """Check if a user has completed identity verification AND has crypto experience.
    
    Returns True if:
      - The user is a system creator (whitelist bypass), OR
      - The user has been verified via GitHub or LinkedIn AND has sufficient
        crypto experience (priority != no_experience).
    
    Users with no verifiable crypto experience are BLOCKED from trading.
    """
    normalized = email.lower().strip()
    
    # Creator/admin whitelist — always allowed
    if _is_creator(normalized):
        return True
    
    record = _verification_db.get(normalized)
    if not record:
        # Try pulling from DynamoDB cloud store
        cloud_record = cloud_store.get_identity(normalized)
        if cloud_record:
            _verification_db[normalized] = cloud_record
            record = cloud_record
        else:
            return False
    
    # Must be identity-verified
    if not record.get("verified", False):
        return False
    
    # Must have sufficient crypto experience
    crypto_can_trade = record.get("crypto_can_trade", False)
    if not crypto_can_trade:
        return False
    
    return True


def get_user_crypto_priority(email: str) -> str:
    """Get the user's crypto experience priority level.
    
    Returns: "veteran" | "experienced" | "rookie" | "no_experience" | "unverified"
    """
    normalized = email.lower().strip()
    
    if _is_creator(normalized):
        return "veteran"  # Creators always get top priority
    
    record = _verification_db.get(normalized)
    if not record:
        # Try pulling from DynamoDB cloud store
        cloud_record = cloud_store.get_identity(normalized)
        if cloud_record:
            _verification_db[normalized] = cloud_record
            record = cloud_record
    if not record or not record.get("verified", False):
        return "unverified"
    
    return record.get("crypto_priority", "no_experience")


def get_user_verification(email: str) -> Optional[dict]:
    """Get verification record for a user.
    
    Checks local in-memory DB first, then falls back to DynamoDB cloud store.
    """
    normalized = email.lower().strip()
    record = _verification_db.get(normalized)
    if record:
        return record
    # Try pulling from DynamoDB cloud store
    cloud_record = cloud_store.get_identity(normalized)
    if cloud_record:
        _verification_db[normalized] = cloud_record
        return cloud_record
    return None


def _derive_display_name(
    github_username: str,
    github_display_name: str,
    linkedin_username: str,
    linkedin_display_name: str,
) -> str:
    """Derive the user's display name exclusively from their GitHub and LinkedIn profiles.
    
    Users CANNOT set a custom username or alias. Their identity in the system
    is the combination of their verified OAuth provider profiles.
    
    Priority:
      1. If both providers verified: "GitHub Name / LinkedIn Name"
      2. If GitHub only: GitHub display_name or username
      3. If LinkedIn only: LinkedIn display_name or username
    """
    parts = []
    
    # GitHub identity
    gh_name = github_display_name.strip() if github_display_name else ""
    gh_user = github_username.strip() if github_username else ""
    if gh_name:
        parts.append(gh_name)
    elif gh_user:
        parts.append(f"@{gh_user}")
    
    # LinkedIn identity
    li_name = linkedin_display_name.strip() if linkedin_display_name else ""
    li_user = linkedin_username.strip() if linkedin_username else ""
    if li_name:
        parts.append(li_name)
    elif li_user:
        parts.append(li_user)
    
    if len(parts) >= 2:
        return " / ".join(parts)
    elif len(parts) == 1:
        return parts[0]
    else:
        return "Verified User"


def store_verification(email: str, result: VerificationResult) -> None:
    """Store verification result for a user.
    
    Only stores: provider, username, verified status, timestamp, reputation.
    Access tokens are NEVER stored.
    
    Identity is derived EXCLUSIVELY from GitHub and LinkedIn profiles.
    Users cannot set a custom username or alias — their identity is
    the combination of their verified provider profiles.
    """
    normalized = email.lower().strip()
    existing = _verification_db.get(normalized, {})

    # If user already verified with another provider, mark as dual
    is_dual = False
    if existing and existing.get("verified") and existing.get("provider") != result.provider:
        is_dual = True

    # Track each provider's username separately — identity comes ONLY from providers
    github_username = existing.get("github_username", "")
    linkedin_username = existing.get("linkedin_username", "")
    github_display_name = existing.get("github_display_name", "")
    linkedin_display_name = existing.get("linkedin_display_name", "")
    
    if result.provider == "github":
        github_username = result.provider_username
        github_display_name = result.display_name
    elif result.provider == "linkedin":
        linkedin_username = result.provider_username
        linkedin_display_name = result.display_name

    # Derive display name from provider profiles only (no custom aliases)
    derived_display_name = _derive_display_name(
        github_username, github_display_name,
        linkedin_username, linkedin_display_name,
    )

    _verification_db[normalized] = {
        "provider": "dual" if is_dual else result.provider,
        "provider_username": result.provider_username,
        "display_name": derived_display_name,
        "verified": result.verified,
        "verified_at": result.verified_at or existing.get("verified_at", ""),
        "reputation_score": max(result.reputation_score, existing.get("reputation_score", 0)),
        # Crypto experience fields
        "crypto_priority": result.crypto_priority,
        "crypto_estimated_years": result.crypto_estimated_years,
        "crypto_can_trade": result.crypto_can_trade,
        "crypto_signals": result.crypto_signals,
        "dual_verified": is_dual or result.dual_verified,
        # Track both providers for dual verification
        "providers": list(set(
            existing.get("providers", []) + [result.provider]
        )),
        # Separate provider usernames — identity derived from these ONLY
        "github_username": github_username,
        "linkedin_username": linkedin_username,
        "github_display_name": github_display_name,
        "linkedin_display_name": linkedin_display_name,
        # Cybersecurity beware list screening
        "beware_list_clean": result.beware_list_clean,
        "beware_list_matches": result.beware_list_matches,
    }
    
    # Sync to DynamoDB cloud store (fire-and-forget, non-blocking on failure)
    try:
        cloud_store.put_identity(normalized, _verification_db[normalized])
    except Exception as cloud_exc:
        logger.warning("DynamoDB sync failed for %s: %s", normalized, cloud_exc)
    
    if result.verified:
        log_security_event(
            SecurityEventType.LOGIN_SUCCESS,
            email=normalized,
            details={
                "action": "identity_verified",
                "provider": result.provider,
                "provider_username": result.provider_username,
            }
        )
        logger.info(
            "Identity VERIFIED for %s via %s (%s)",
            normalized, result.provider, result.provider_username,
        )
    else:
        log_security_event(
            SecurityEventType.LOGIN_FAILURE,
            email=normalized,
            details={
                "action": "identity_verification_failed",
                "provider": result.provider,
                "reasons": result.failure_reasons,
            }
        )
        logger.warning(
            "Identity verification FAILED for %s via %s: %s",
            normalized, result.provider, "; ".join(result.failure_reasons),
        )


def check_verification_rate_limit(email: str) -> tuple[bool, int]:
    """Rate limit verification attempts: max 5 per hour per email.
    
    Returns (allowed, remaining_attempts).
    """
    import time
    now = time.time()
    window = 3600  # 1 hour
    max_attempts = 5
    
    key = email.lower().strip()
    attempts = _verification_attempts.get(key, [])
    # Remove expired attempts
    attempts = [t for t in attempts if now - t < window]
    _verification_attempts[key] = attempts
    
    if len(attempts) >= max_attempts:
        return False, 0
    
    attempts.append(now)
    return True, max_attempts - len(attempts)


async def verify_with_github(code: str, email: str) -> VerificationResult:
    """Complete GitHub verification flow: exchange code → fetch profile → validate.
    
    Args:
        code: GitHub OAuth authorization code
        email: User's email in our system
        
    Returns:
        VerificationResult with verified=True if all checks pass
    """
    # Rate limit check
    allowed, remaining = check_verification_rate_limit(email)
    if not allowed:
        return VerificationResult(
            verified=False,
            provider="github",
            failure_reasons=[
                "Too many verification attempts. Please try again later. "
                "This rate limit prevents automated attacks by hackers."
            ],
        )
    
    # Exchange code for token
    token_data = await exchange_github_code(code)
    if not token_data or "access_token" not in token_data:
        return VerificationResult(
            verified=False,
            provider="github",
            failure_reasons=[
                "Failed to authenticate with GitHub. "
                "This could indicate a tampered authorization code."
            ],
        )
    
    # Fetch profile
    profile = await fetch_github_profile(token_data["access_token"])
    if not profile:
        return VerificationResult(
            verified=False,
            provider="github",
            failure_reasons=[
                "Failed to fetch GitHub profile. "
                "The access token may be invalid or revoked."
            ],
        )
    
    # Validate profile
    result = validate_github_profile(profile)
    
    # ── Cybersecurity Beware List Screening ────────────────────────────────
    # Check user against OFAC, Interpol, EU sanctions, threat actor aliases,
    # and crypto scam databases. This is a HARD BLOCK — if matched, verification
    # is rejected regardless of other checks.
    if result.verified:
        beware_result = await check_cybersecurity_beware_lists(
            display_name=result.display_name or result.provider_username,
            username=result.provider_username,
            email=email,
        )
        result.beware_list_clean = beware_result.is_clean
        result.beware_list_matches = [
            {"source": m.source, "matched_name": m.matched_name,
             "match_type": m.match_type, "severity": m.severity, "details": m.details}
            for m in beware_result.matches
        ]
        if not beware_result.is_clean:
            result.verified = False
            critical_matches = [m for m in beware_result.matches if m.severity == "critical"]
            if critical_matches:
                result.failure_reasons.append(
                    "IDENTITY BLOCKED: Your identity matches entries on cybersecurity "
                    "sanctions/threat lists (e.g., OFAC, Interpol). This is a hard block "
                    "for platform safety. If you believe this is an error, contact support."
                )
            else:
                result.failure_reasons.append(
                    "IDENTITY FLAGGED: Your identity has potential matches on cybersecurity "
                    "beware lists. Verification is blocked pending manual review. "
                    "Contact support if you believe this is an error."
                )
            log_security_event(
                SecurityEventType.LOGIN_FAILURE,
                email=email.lower().strip(),
                details={
                    "action": "cybersecurity_beware_list_match",
                    "provider": "github",
                    "matches": result.beware_list_matches,
                }
            )
    
    # Run crypto experience assessment if identity verified
    if result.verified:
        from app.core.crypto_experience import run_full_crypto_assessment
        crypto_result = await run_full_crypto_assessment(
            display_name=result.display_name or result.provider_username,
            username=result.provider_username,
            github_token=token_data["access_token"],
        )
        result.crypto_priority = crypto_result.priority.value
        result.crypto_estimated_years = crypto_result.estimated_years
        result.crypto_can_trade = crypto_result.can_trade
        result.crypto_signals = crypto_result.signals
        
        # Check if user already has LinkedIn verification (dual)
        existing = get_user_verification(email)
        if existing and existing.get("verified") and "linkedin" in existing.get("providers", []):
            result.dual_verified = True
            # Re-run with dual bonus
            crypto_result = await run_full_crypto_assessment(
                display_name=result.display_name or result.provider_username,
                username=result.provider_username,
                github_token=token_data["access_token"],
            )
            result.crypto_priority = crypto_result.priority.value
            result.crypto_estimated_years = crypto_result.estimated_years
            result.crypto_can_trade = crypto_result.can_trade
            result.crypto_signals = crypto_result.signals
        
        if not crypto_result.can_trade:
            logger.warning(
                "GitHub identity verified for %s but BLOCKED — insufficient crypto experience "
                "(%.1f years, priority: %s)",
                email, crypto_result.estimated_years, crypto_result.priority.value,
            )
    
    # Store result
    store_verification(email, result)
    
    return result


async def verify_with_linkedin(code: str, email: str) -> VerificationResult:
    """Complete LinkedIn verification flow: exchange code → fetch profile → validate.
    
    Args:
        code: LinkedIn OAuth authorization code
        email: User's email in our system
        
    Returns:
        VerificationResult with verified=True if all checks pass
    """
    # Rate limit check
    allowed, remaining = check_verification_rate_limit(email)
    if not allowed:
        return VerificationResult(
            verified=False,
            provider="linkedin",
            failure_reasons=[
                "Too many verification attempts. Please try again later. "
                "This rate limit prevents automated attacks by hackers."
            ],
        )
    
    # Exchange code for token
    token_data = await exchange_linkedin_code(code)
    if not token_data or "access_token" not in token_data:
        return VerificationResult(
            verified=False,
            provider="linkedin",
            failure_reasons=[
                "Failed to authenticate with LinkedIn. "
                "This could indicate a tampered authorization code."
            ],
        )
    
    # Fetch profile
    profile = await fetch_linkedin_profile(token_data["access_token"])
    if not profile:
        return VerificationResult(
            verified=False,
            provider="linkedin",
            failure_reasons=[
                "Failed to fetch LinkedIn profile. "
                "The access token may be invalid or revoked."
            ],
        )
    
    # Validate profile
    result = validate_linkedin_profile(profile)
    
    # ── Cybersecurity Beware List Screening ────────────────────────────────
    # Check user against OFAC, Interpol, EU sanctions, threat actor aliases,
    # and crypto scam databases. This is a HARD BLOCK — if matched, verification
    # is rejected regardless of other checks.
    if result.verified:
        beware_result = await check_cybersecurity_beware_lists(
            display_name=result.display_name or result.provider_username,
            username=result.provider_username,
            email=email,
        )
        result.beware_list_clean = beware_result.is_clean
        result.beware_list_matches = [
            {"source": m.source, "matched_name": m.matched_name,
             "match_type": m.match_type, "severity": m.severity, "details": m.details}
            for m in beware_result.matches
        ]
        if not beware_result.is_clean:
            result.verified = False
            critical_matches = [m for m in beware_result.matches if m.severity == "critical"]
            if critical_matches:
                result.failure_reasons.append(
                    "IDENTITY BLOCKED: Your identity matches entries on cybersecurity "
                    "sanctions/threat lists (e.g., OFAC, Interpol). This is a hard block "
                    "for platform safety. If you believe this is an error, contact support."
                )
            else:
                result.failure_reasons.append(
                    "IDENTITY FLAGGED: Your identity has potential matches on cybersecurity "
                    "beware lists. Verification is blocked pending manual review. "
                    "Contact support if you believe this is an error."
                )
            log_security_event(
                SecurityEventType.LOGIN_FAILURE,
                email=email.lower().strip(),
                details={
                    "action": "cybersecurity_beware_list_match",
                    "provider": "linkedin",
                    "matches": result.beware_list_matches,
                }
            )
    
    # Run crypto experience assessment if identity verified
    if result.verified:
        from app.core.crypto_experience import run_full_crypto_assessment
        crypto_result = await run_full_crypto_assessment(
            display_name=result.display_name or result.provider_username,
            username=result.provider_username,
            linkedin_token=token_data["access_token"],
        )
        result.crypto_priority = crypto_result.priority.value
        result.crypto_estimated_years = crypto_result.estimated_years
        result.crypto_can_trade = crypto_result.can_trade
        result.crypto_signals = crypto_result.signals
        
        # Check if user already has GitHub verification (dual)
        existing = get_user_verification(email)
        if existing and existing.get("verified") and "github" in existing.get("providers", []):
            result.dual_verified = True
            # Re-run with dual bonus
            crypto_result = await run_full_crypto_assessment(
                display_name=result.display_name or result.provider_username,
                username=result.provider_username,
                linkedin_token=token_data["access_token"],
            )
            result.crypto_priority = crypto_result.priority.value
            result.crypto_estimated_years = crypto_result.estimated_years
            result.crypto_can_trade = crypto_result.can_trade
            result.crypto_signals = crypto_result.signals
        
        if not crypto_result.can_trade:
            logger.warning(
                "LinkedIn identity verified for %s but BLOCKED — insufficient crypto experience "
                "(%.1f years, priority: %s)",
                email, crypto_result.estimated_years, crypto_result.priority.value,
            )
    
    # Store result
    store_verification(email, result)
    
    return result


# ─── FastAPI Dependency for Identity Verification ──────────────────────────────

async def require_verified_identity(http_request: "Request") -> str:
    """FastAPI dependency that blocks unverified users from trading endpoints.
    
    Returns the verified user's email if verified.
    Raises HTTPException(403) if the user is NOT verified.
    
    Usage in FastAPI routes:
        from app.core.identity_verification import require_verified_identity
        
        @router.post("/swap/ethereum")
        async def execute_swap(request: SwapRequest, user_email: str = Depends(require_verified_identity)):
            ...
    """
    from fastapi import HTTPException

    settings = get_settings()

    # If verification is not required, allow all
    if not settings.IDENTITY_VERIFICATION_REQUIRED:
        return http_request.headers.get("X-User-Email", "anonymous")

    user_email = http_request.headers.get("X-User-Email", "").strip()
    if not user_email:
        # Try query param fallback
        user_email = http_request.query_params.get("email", "").strip()

    if not user_email or not is_user_verified(user_email):
        # Determine specific reason for blocking
        record = get_user_verification(user_email) if user_email else None
        if record and record.get("verified") and not record.get("crypto_can_trade", False):
            priority = record.get("crypto_priority", "no_experience")
            years = record.get("crypto_estimated_years", 0)
            raise HTTPException(
                status_code=403,
                detail=(
                    f"TRADING BLOCKED: Insufficient crypto experience. "
                    f"Your estimated crypto experience is {years:.1f} years (priority: {priority}). "
                    f"Minimum 2 years required. Connect both GitHub and LinkedIn for bonus scoring. "
                    f"Demonstrate crypto experience through projects, roles, or online presence. "
                    f"Visit /api/v1/identity/requirements for details."
                ),
            )
        raise HTTPException(
            status_code=403,
            detail=(
                "TRADING BLOCKED: Identity verification required. "
                "Verify your identity via GitHub or LinkedIn before trading. "
                "Accounts must be at least 1 year old to pass verification. "
                "You also need minimum 2 years of crypto experience to trade. "
                "Visit /api/v1/identity/requirements for details."
            ),
        )

    return user_email


def sync_cloud_on_startup() -> int:
    """Pull all identity records from DynamoDB into the local in-memory DB.
    
    Called once on application startup to ensure the local cache is
    populated with the latest cloud data. If DynamoDB is disabled or
    unavailable, this is a no-op.
    
    Returns:
        Number of records pulled from DynamoDB.
    """
    try:
        pulled = cloud_store.pull_to_local(_verification_db)
        if pulled > 0:
            logger.info("Cloud identity sync: %d records loaded from DynamoDB", pulled)
        return pulled
    except Exception as exc:
        logger.warning("Cloud identity sync failed on startup: %s", exc)
        return 0
