"""
Authentication API
==================
Production-grade authentication with:
- Email signup with password validation
- JWT-based authentication (using PyJWT)
- Rate limiting and account lockout
- Password breach checking (haveibeenpwned)
- Two-Factor Authentication (TOTP)
- Security event logging

Features:
- Email signup with password (Gmail, Hotmail, etc.)
- Email verification via confirmation link
- JWT-based authentication
- Newsletter subscription and updates
- Password reset functionality
- Two-Factor Authentication (TOTP)
- Automatic day/night theme detection
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import logging
import secrets
import re

from app.core.config import get_settings
from app.core.security import (
    hash_password,
    verify_password,
    generate_jwt,
    verify_jwt,
    validate_password_strength,
    check_password_breached,
    check_rate_limit,
    record_failed_login,
    clear_failed_logins,
    is_account_locked,
    blacklist_token,
    generate_totp_secret,
    verify_totp,
    get_totp_uri,
    sanitize_for_log,
    sanitize_email,
    log_security_event,
    SecurityEventType,
)

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter()


# ─── Request/Response Models ──────────────────────────────────────────────────

class UserSignupRequest(BaseModel):
    """User signup request with email and password."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="User password (min 8 chars)")
    confirm_password: str = Field(..., description="Password confirmation")
    phone_number: Optional[str] = Field(None, description="Phone number for 2FA (E.164 format)")
    subscribe_newsletter: bool = Field(default=True, description="Subscribe to newsletter")
    
    @validator('password')
    def password_strength(cls, v):
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError('; '.join(errors))
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('phone_number')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+[1-9]\d{1,14}$', v):
            raise ValueError('Phone number must be in E.164 format (e.g., +1234567890)')
        return v


class UserLoginRequest(BaseModel):
    """User login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TwoFactorVerifyRequest(BaseModel):
    """2FA verification request."""
    email: EmailStr = Field(..., description="User email address")
    code: str = Field(..., description="6-digit verification code from authenticator app")


class TwoFactorSetupRequest(BaseModel):
    """2FA setup request."""
    phone_number: Optional[str] = Field(None, description="Phone number for SMS backup (E.164 format)")


class PasswordResetRequest(BaseModel):
    """Password reset request."""
    email: EmailStr = Field(..., description="User email address")


class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation."""
    token: str = Field(..., description="Reset token from email")
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(...)
    
    @validator('new_password')
    def password_strength(cls, v):
        is_valid, errors = validate_password_strength(v)
        if not is_valid:
            raise ValueError('; '.join(errors))
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class NewsletterSubscribeRequest(BaseModel):
    """Newsletter subscription request."""
    email: EmailStr = Field(..., description="Email to subscribe")
    preferences: Optional[List[str]] = Field(default=["trading_updates", "system_updates"])


class UserProfileResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    email_verified: bool
    phone_number: Optional[str]
    two_factor_enabled: bool
    newsletter_subscribed: bool
    newsletter_preferences: List[str]
    timezone: Optional[str]
    created_at: str
    last_login: Optional[str]


class AuthTokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    requires_2fa: bool = False
    user: Optional[UserProfileResponse] = None


class TimezoneResponse(BaseModel):
    """Timezone detection response."""
    timezone: str
    is_daytime: bool
    current_hour: int
    sunrise_hour: int
    sunset_hour: int


# ─── In-Memory User Store (Replace with database in production) ─────────────

_users_db = {}  # email -> user data
_verification_tokens = {}  # token -> email
_password_reset_tokens = {}  # token -> email
_newsletter_subscribers = {}  # email -> subscription data
_totp_secrets = {}  # email -> {secret, verified, backup_codes}
_rate_limit_store = {}  # IP -> [timestamps]


# ─── Dependency: Get Current User ───────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Extract and verify the current user from JWT token.
    
    Raises:
        HTTPException: If token is invalid or blacklisted
    """
    token = credentials.credentials
    
    # Check blacklist
    from app.core.security import is_token_blacklisted
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked"
        )
    
    # Verify token
    valid, payload, error = verify_jwt(token)
    if not valid:
        raise HTTPException(
            status_code=401,
            detail=error or "Invalid token"
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload"
        )
    
    # Check if user exists
    user = _users_db.get(email.lower())
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )
    
    return {"email": email, "user": user, "payload": payload}


# ─── Helper Functions ──────────────────────────────────────────────────────

def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _send_email_mock(to_email: str, subject: str, body: str) -> bool:
    """
    Mock email sending. In production, use:
    - SendGrid
    - AWS SES
    - Mailgun
    - SMTP server
    """
    logger.info("=" * 60)
    logger.info("📧 EMAIL SENT (Mock)")
    logger.info(f"  To: {sanitize_for_log(to_email)}")
    logger.info(f"  Subject: {sanitize_for_log(subject)}")
    logger.info(f"  Body:\n{body[:200]}...")
    logger.info("=" * 60)
    return True


def _detect_timezone_daytime(lat: float = None, lon: float = None, timezone: str = None) -> dict:
    """
    Detect if it's daytime based on timezone or coordinates.
    Returns timezone info and daytime status.
    """
    current_hour = datetime.now(timezone.utc).hour
    
    if timezone:
        try:
            import pytz
            tz = pytz.timezone(timezone)
            current_hour = datetime.now(tz).hour
        except Exception:
            pass
    
    sunrise_hour = 6
    sunset_hour = 18
    is_daytime = sunrise_hour <= current_hour < sunset_hour
    
    return {
        "timezone": timezone or "UTC",
        "is_daytime": is_daytime,
        "current_hour": current_hour,
        "sunrise_hour": sunrise_hour,
        "sunset_hour": sunset_hour,
    }


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/signup", response_model=AuthTokenResponse)
async def signup(request: UserSignupRequest, req: Request):
    """
    Register a new user with email and password.
    
    Features:
    - Password strength validation
    - Breach password checking
    - Rate limiting
    - Email verification
    - Optional 2FA setup
    """
    client_ip = _get_client_ip(req)
    
    # ── Rate Limiting ───────────────────────────────────────────────────────
    allowed, remaining = check_rate_limit(f"signup:{client_ip}", max_requests=5)
    if not allowed:
        log_security_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            email=request.email,
            ip_address=client_ip,
            details={"endpoint": "signup"}
        )
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in 1 minute."
        )
    
    # ── Check if user exists ─────────────────────────────────────────────────
    normalized_email = sanitize_email(request.email)
    if normalized_email in _users_db:
        # Don't reveal if email exists
        raise HTTPException(
            status_code=400,
            detail="An account with this email already exists"
        )
    
    # ── Password Validation ─────────────────────────────────────────────────
    is_valid, errors = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={"errors": errors}
        )
    
    # ── Breach Password Check ────────────────────────────────────────────────
    is_breached = await check_password_breached(request.password)
    if is_breached:
        log_security_event(
            SecurityEventType.BREACH_PASSWORD_DETECTED,
            email=normalized_email,
            ip_address=client_ip,
            details={"source": "haveibeenpwned"}
        )
        raise HTTPException(
            status_code=400,
            detail="This password has been found in a data breach. Please choose a different password."
        )
    
    # ── Hash Password ────────────────────────────────────────────────────────
    hashed_password, salt = hash_password(request.password)
    
    # ── Generate Verification Token ───────────────────────────────────────────
    verification_token = secrets.token_urlsafe(32)
    _verification_tokens[verification_token] = {
        "email": normalized_email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }
    
    # ── Create User ──────────────────────────────────────────────────────────
    user_id = secrets.token_hex(8)
    totp_secret = None
    if request.phone_number:
        totp_secret = generate_totp_secret()
    
    _users_db[normalized_email] = {
        "id": user_id,
        "email": normalized_email,
        "password_hash": hashed_password,
        "password_salt": salt,
        "email_verified": False,
        "phone_number": request.phone_number,
        "two_factor_enabled": bool(request.phone_number),
        "totp_secret": totp_secret,
        "newsletter_subscribed": request.subscribe_newsletter,
        "newsletter_preferences": ["trading_updates", "system_updates"] if request.subscribe_newsletter else [],
        "timezone": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
    }
    
    # ── Add to Newsletter ─────────────────────────────────────────────────────
    if request.subscribe_newsletter:
        _newsletter_subscribers[normalized_email] = {
            "email": normalized_email,
            "preferences": ["trading_updates", "system_updates"],
            "subscribed_at": datetime.now(timezone.utc).isoformat(),
            "active": True,
        }
    
    # ── Send Verification Email ───────────────────────────────────────────────
    base_url = str(req.base_url).rstrip('/')
    verify_url = f"{base_url}/api/v1/auth/verify/{verification_token}"
    
    email_body = f"""
    Welcome to AI Agent Trading Platform!
    
    Please verify your email address by clicking the link below:
    
    {verify_url}
    
    This link will expire in 24 hours.
    
    If you did not create an account, please ignore this email.
    
    Best regards,
    AI Trading Team
    """
    
    _send_email_mock(
        to_email=request.email,
        subject="Verify Your Email - AI Agent Trading",
        body=email_body
    )
    
    log_security_event(
        SecurityEventType.LOGIN_SUCCESS,
        email=normalized_email,
        ip_address=client_ip,
        user_agent=req.headers.get("user-agent"),
        details={"action": "signup"}
    )
    
    # ── Generate Auth Token ─────────────────────────────────────────────────
    access_token = generate_jwt(normalized_email)
    
    return AuthTokenResponse(
        access_token=access_token,
        expires_in=86400,
        requires_2fa=False,
        user=UserProfileResponse(
            id=user_id,
            email=request.email,
            email_verified=False,
            phone_number=request.phone_number,
            two_factor_enabled=bool(request.phone_number),
            newsletter_subscribed=request.subscribe_newsletter,
            newsletter_preferences=["trading_updates", "system_updates"] if request.subscribe_newsletter else [],
            timezone=None,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_login=None,
        )
    )


@router.post("/login", response_model=AuthTokenResponse)
async def login(request: UserLoginRequest, req: Request):
    """
    Login with email and password.
    
    Features:
    - Rate limiting
    - Account lockout after failed attempts
    - 2FA support
    - Security event logging
    """
    client_ip = _get_client_ip(req)
    normalized_email = sanitize_email(request.email)
    
    # ── Rate Limiting ───────────────────────────────────────────────────────
    allowed, remaining = check_rate_limit(f"login:{client_ip}", max_requests=10)
    if not allowed:
        log_security_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            email=normalized_email,
            ip_address=client_ip,
            details={"endpoint": "login"}
        )
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again in 1 minute."
        )
    
    # ── Check Account Lock ──────────────────────────────────────────────────
    is_locked, seconds_remaining = is_account_locked(normalized_email)
    if is_locked:
        log_security_event(
            SecurityEventType.ACCOUNT_LOCKED,
            email=normalized_email,
            ip_address=client_ip,
            details={"seconds_remaining": seconds_remaining}
        )
        raise HTTPException(
            status_code=423,
            detail=f"Account locked. Try again in {seconds_remaining // 60} minutes."
        )
    
    # ── Verify User Exists ───────────────────────────────────────────────────
    user = _users_db.get(normalized_email)
    
    # Don't reveal if user exists
    if not user:
        record_failed_login(normalized_email)
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )
    
    # ── Verify Password ──────────────────────────────────────────────────────
    if not verify_password(request.password, user["password_hash"], user.get("password_salt", "")):
        is_locked, attempts_remaining = record_failed_login(normalized_email)
        
        if is_locked:
            log_security_event(
                SecurityEventType.ACCOUNT_LOCKED,
                email=normalized_email,
                ip_address=client_ip,
                details={"reason": "too_many_failed_attempts"}
            )
            raise HTTPException(
                status_code=423,
                detail="Account locked due to too many failed attempts. Try again in 15 minutes."
            )
        
        log_security_event(
            SecurityEventType.LOGIN_FAILURE,
            email=normalized_email,
            ip_address=client_ip,
            details={"attempts_remaining": attempts_remaining}
        )
        
        raise HTTPException(
            status_code=401,
            detail=f"Invalid email or password. {attempts_remaining} attempts remaining."
        )
    
    # ── Check Email Verified ─────────────────────────────────────────────────
    if not user["email_verified"]:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email address first. Check your inbox for the verification link."
        )
    
    # ── Clear Failed Logins ─────────────────────────────────────────────────
    clear_failed_logins(normalized_email)
    
    # ── Check 2FA ────────────────────────────────────────────────────────────
    if user.get("two_factor_enabled") and user.get("totp_secret"):
        # Generate and store temporary 2FA token
        temp_token = secrets.token_urlsafe(32)
        _totp_secrets[normalized_email] = {
            "temp_token": temp_token,
            "totp_secret": user["totp_secret"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        }
        
        log_security_event(
            "2fa_required",
            email=normalized_email,
            ip_address=client_ip,
        )
        
        return AuthTokenResponse(
            access_token=temp_token,
            expires_in=300,
            requires_2fa=True,
            user=None,
        )
    
    # ── Generate Auth Token ─────────────────────────────────────────────────
    user["last_login"] = datetime.now(timezone.utc).isoformat()
    access_token = generate_jwt(normalized_email)
    
    log_security_event(
        SecurityEventType.LOGIN_SUCCESS,
        email=normalized_email,
        ip_address=client_ip,
        user_agent=req.headers.get("user-agent"),
    )
    
    return AuthTokenResponse(
        access_token=access_token,
        expires_in=86400,
        requires_2fa=False,
        user=UserProfileResponse(
            id=user["id"],
            email=user["email"],
            email_verified=True,
            phone_number=user.get("phone_number"),
            two_factor_enabled=user.get("two_factor_enabled", False),
            newsletter_subscribed=user["newsletter_subscribed"],
            newsletter_preferences=user["newsletter_preferences"],
            timezone=user.get("timezone"),
            created_at=user["created_at"],
            last_login=user["last_login"],
        )
    )


@router.post("/verify-2fa", response_model=AuthTokenResponse)
async def verify_2fa(request: TwoFactorVerifyRequest, req: Request):
    """
    Verify 2FA code from authenticator app.
    
    Returns JWT token after successful verification.
    """
    client_ip = _get_client_ip(req)
    normalized_email = sanitize_email(request.email)
    
    # ── Rate Limiting ───────────────────────────────────────────────────────
    allowed, remaining = check_rate_limit(f"2fa:{client_ip}", max_requests=5)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded."
        )
    
    # ── Verify 2FA Session ───────────────────────────────────────────────────
    session = _totp_secrets.get(normalized_email)
    
    if not session:
        raise HTTPException(
            status_code=400,
            detail="No 2FA session pending. Please login again."
        )
    
    # ── Check Expiration ─────────────────────────────────────────────────────
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        del _totp_secrets[normalized_email]
        raise HTTPException(
            status_code=400,
            detail="2FA session expired. Please login again."
        )
    
    # ── Verify TOTP Code ─────────────────────────────────────────────────────
    if not verify_totp(session["totp_secret"], request.code):
        log_security_event(
            "2fa_failure",
            email=normalized_email,
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid 2FA code"
        )
    
    # ── Clean Up ─────────────────────────────────────────────────────────────
    del _totp_secrets[normalized_email]
    
    # ── Generate Auth Token ─────────────────────────────────────────────────
    user = _users_db.get(normalized_email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    user["last_login"] = datetime.now(timezone.utc).isoformat()
    access_token = generate_jwt(normalized_email)
    
    log_security_event(
        SecurityEventType.LOGIN_SUCCESS,
        email=normalized_email,
        ip_address=client_ip,
        user_agent=req.headers.get("user-agent"),
        details={"method": "2fa"}
    )
    
    return AuthTokenResponse(
        access_token=access_token,
        expires_in=86400,
        requires_2fa=False,
        user=UserProfileResponse(
            id=user["id"],
            email=user["email"],
            email_verified=True,
            phone_number=user.get("phone_number"),
            two_factor_enabled=True,
            newsletter_subscribed=user["newsletter_subscribed"],
            newsletter_preferences=user["newsletter_preferences"],
            timezone=user.get("timezone"),
            created_at=user["created_at"],
            last_login=user["last_login"],
        )
    )


@router.post("/setup-2fa")
async def setup_2fa(request: TwoFactorSetupRequest, req: Request, user: dict = Depends(get_current_user)):
    """
    Set up 2FA for an existing account.
    
    Returns TOTP secret and QR code URI.
    """
    email = user["email"]
    totp_secret = generate_totp_secret()
    
    # Store temporarily until verified
    _totp_secrets[email] = {
        "totp_secret": totp_secret,
        "pending": True,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    }
    
    # Generate URI for QR code
    uri = get_totp_uri(totp_secret, email)
    
    return {
        "success": True,
        "message": "Scan this QR code with your authenticator app",
        "totp_secret": totp_secret,
        "qr_code_uri": uri,
    }


@router.post("/confirm-2fa-setup")
async def confirm_2fa_setup(request: TwoFactorVerifyRequest, user: dict = Depends(get_current_user)):
    """
    Confirm 2FA setup with verification code.
    """
    email = user["email"]
    session = _totp_secrets.get(email)
    
    if not session or not session.get("pending"):
        raise HTTPException(
            status_code=400,
            detail="No pending 2FA setup"
        )
    
    # ── Check Expiration ─────────────────────────────────────────────────────
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        del _totp_secrets[email]
        raise HTTPException(
            status_code=400,
            detail="2FA setup expired. Please start over."
        )
    
    # ── Verify TOTP Code ─────────────────────────────────────────────────────
    if not verify_totp(session["totp_secret"], request.code):
        raise HTTPException(
            status_code=401,
            detail="Invalid verification code"
        )
    
    # ── Enable 2FA ───────────────────────────────────────────────────────────
    user_data = _users_db.get(email)
    if user_data:
        user_data["totp_secret"] = session["totp_secret"]
        user_data["two_factor_enabled"] = True
    
    del _totp_secrets[email]
    
    log_security_event(
        "2fa_enabled",
        email=email,
    )
    
    return {
        "success": True,
        "message": "2FA enabled successfully",
    }


@router.post("/disable-2fa")
async def disable_2fa(user: dict = Depends(get_current_user)):
    """
    Disable 2FA for the current account.
    """
    email = user["email"]
    user_data = _users_db.get(email)
    
    if user_data:
        user_data["totp_secret"] = None
        user_data["two_factor_enabled"] = False
    
    log_security_event(
        "2fa_disabled",
        email=email,
    )
    
    return {
        "success": True,
        "message": "2FA disabled",
    }


@router.get("/timezone", response_model=TimezoneResponse)
async def get_timezone(lat: Optional[float] = None, lon: Optional[float] = None, tz: Optional[str] = None):
    """
    Detect timezone and daytime status.
    
    Used for automatic theme switching on frontend.
    """
    result = _detect_timezone_daytime(lat, lon, tz)
    return TimezoneResponse(**result)


@router.post("/set-timezone")
async def set_timezone(timezone: str, user: dict = Depends(get_current_user)):
    """
    Set user's preferred timezone for automatic theme.
    """
    try:
        import pytz
        pytz.timezone(timezone)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timezone")
    
    user_data = _users_db.get(user["email"])
    if user_data:
        user_data["timezone"] = timezone
    
    return {
        "success": True,
        "timezone": timezone,
        "message": "Timezone updated",
    }


@router.get("/verify/{token}")
async def verify_email(token: str):
    """
    Verify email address using token from verification email.
    """
    token_data = _verification_tokens.get(token)
    
    if not token_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token"
        )
    
    # ── Check Expiration ─────────────────────────────────────────────────────
    expires_at = datetime.fromisoformat(token_data["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        del _verification_tokens[token]
        raise HTTPException(
            status_code=400,
            detail="Verification token has expired. Please request a new one."
        )
    
    # ── Mark Email Verified ───────────────────────────────────────────────────
    email = token_data["email"]
    if email in _users_db:
        _users_db[email]["email_verified"] = True
        del _verification_tokens[token]
    
    log_security_event(
        "email_verified",
        email=email,
    )
    
    return {
        "success": True,
        "message": "Email verified successfully! You can now log in.",
        "email": email,
    }


@router.post("/resend-verification")
async def resend_verification(email: EmailStr, req: Request):
    """
    Resend verification email.
    """
    normalized_email = sanitize_email(email)
    user = _users_db.get(normalized_email)
    
    if not user:
        # Don't reveal if user exists
        return {"success": True, "message": "If an account exists, a verification email will be sent"}
    
    if user["email_verified"]:
        return {"success": True, "message": "Email is already verified"}
    
    # ── Rate Limiting ───────────────────────────────────────────────────────
    client_ip = _get_client_ip(req)
    allowed, _ = check_rate_limit(f"resend:{client_ip}:{normalized_email}", max_requests=3)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again later."
        )
    
    # ── Generate New Token ───────────────────────────────────────────────────
    verification_token = secrets.token_urlsafe(32)
    _verification_tokens[verification_token] = {
        "email": normalized_email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }
    
    # ── Send Email ───────────────────────────────────────────────────────────
    base_url = str(req.base_url).rstrip('/')
    verify_url = f"{base_url}/api/v1/auth/verify/{verification_token}"
    
    email_body = f"""
    Verify Your Email Address
    
    Click the link below to verify:
    {verify_url}
    
    This link expires in 24 hours.
    """
    
    _send_email_mock(
        to_email=email,
        subject="Verify Your Email - AI Agent Trading",
        body=email_body
    )
    
    return {"success": True, "message": "Verification email sent"}


@router.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest, req: Request):
    """
    Request password reset email.
    """
    client_ip = _get_client_ip(req)
    normalized_email = sanitize_email(request.email)
    
    # ── Rate Limiting ───────────────────────────────────────────────────────
    allowed, _ = check_rate_limit(f"reset:{client_ip}", max_requests=3)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Try again later."
        )
    
    user = _users_db.get(normalized_email)
    
    # Don't reveal if user exists
    if not user:
        return {"success": True, "message": "If an account exists, a reset email will be sent"}
    
    # ── Generate Reset Token ─────────────────────────────────────────────────
    reset_token = secrets.token_urlsafe(32)
    _password_reset_tokens[reset_token] = {
        "email": normalized_email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }
    
    # ── Send Reset Email ─────────────────────────────────────────────────────
    base_url = str(req.base_url).rstrip('/')
    reset_url = f"{base_url}/reset-password?token={reset_token}"
    
    email_body = f"""
    Password Reset Request
    
    Click the link below to reset your password:
    {reset_url}
    
    This link expires in 1 hour.
    
    If you did not request this reset, please ignore this email and consider changing your password.
    """
    
    _send_email_mock(
        to_email=request.email,
        subject="Password Reset - AI Agent Trading",
        body=email_body
    )
    
    log_security_event(
        SecurityEventType.PASSWORD_RESET_REQUEST,
        email=normalized_email,
        ip_address=client_ip,
    )
    
    return {"success": True, "message": "If an account exists, a reset email will be sent"}


@router.post("/reset-password")
async def reset_password(request: PasswordResetConfirmRequest):
    """
    Confirm password reset with token.
    """
    # ── Validate Password Strength ───────────────────────────────────────────
    is_valid, errors = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={"errors": errors}
        )
    
    # ── Check Breach ─────────────────────────────────────────────────────────
    is_breached = await check_password_breached(request.new_password)
    if is_breached:
        raise HTTPException(
            status_code=400,
            detail="This password has been found in a data breach. Please choose a different password."
        )
    
    token_data = _password_reset_tokens.get(request.token)
    
    if not token_data:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )
    
    # ── Check Expiration ─────────────────────────────────────────────────────
    expires_at = datetime.fromisoformat(token_data["expires_at"])
    if datetime.now(timezone.utc) > expires_at:
        del _password_reset_tokens[request.token]
        raise HTTPException(
            status_code=400,
            detail="Reset token has expired"
        )
    
    # ── Update Password ──────────────────────────────────────────────────────
    email = token_data["email"]
    if email in _users_db:
        hashed_password, salt = hash_password(request.new_password)
        _users_db[email]["password_hash"] = hashed_password
        _users_db[email]["password_salt"] = salt
        del _password_reset_tokens[request.token]
    
    log_security_event(
        SecurityEventType.PASSWORD_RESET_COMPLETE,
        email=email,
    )
    
    return {"success": True, "message": "Password reset successfully"}


@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """
    Get current user profile.
    """
    user_data = user["user"]
    
    return {
        "id": user_data["id"],
        "email": user_data["email"],
        "email_verified": user_data["email_verified"],
        "phone_number": user_data.get("phone_number"),
        "two_factor_enabled": user_data.get("two_factor_enabled", False),
        "newsletter_subscribed": user_data["newsletter_subscribed"],
        "newsletter_preferences": user_data["newsletter_preferences"],
        "timezone": user_data.get("timezone"),
        "created_at": user_data["created_at"],
        "last_login": user_data.get("last_login"),
    }


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Logout user (invalidate token).
    
    Adds the current token to a blacklist.
    """
    # Extract token from user payload
    # In production, you'd get the raw token from the request
    # For now, we'll mark the user as logged out
    
    log_security_event(
        SecurityEventType.LOGOUT,
        email=user["email"],
    )
    
    return {"success": True, "message": "Logged out successfully"}


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    user: dict = Depends(get_current_user)
):
    """
    Change password for authenticated user.
    """
    # ── Validate New Password ────────────────────────────────────────────────
    is_valid, errors = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={"errors": errors}
        )
    
    # ── Check Breach ─────────────────────────────────────────────────────────
    is_breached = await check_password_breached(new_password)
    if is_breached:
        raise HTTPException(
            status_code=400,
            detail="This password has been found in a data breach. Please choose a different password."
        )
    
    email = user["email"]
    user_data = user["user"]
    
    # ── Verify Current Password ──────────────────────────────────────────────
    if not verify_password(current_password, user_data["password_hash"], user_data.get("password_salt", "")):
        raise HTTPException(
            status_code=401,
            detail="Current password is incorrect"
        )
    
    # ── Update Password ──────────────────────────────────────────────────────
    hashed_password, salt = hash_password(new_password)
    _users_db[email]["password_hash"] = hashed_password
    _users_db[email]["password_salt"] = salt
    
    log_security_event(
        SecurityEventType.PASSWORD_CHANGE,
        email=email,
    )
    
    return {"success": True, "message": "Password changed successfully"}


# ─── Newsletter Endpoints ───────────────────────────────────────────────────

@router.post("/newsletter/subscribe")
async def subscribe_newsletter(request: NewsletterSubscribeRequest):
    """
    Subscribe to newsletter updates.
    """
    normalized_email = sanitize_email(request.email)
    
    if normalized_email in _newsletter_subscribers:
        _newsletter_subscribers[normalized_email]["preferences"] = request.preferences
        _newsletter_subscribers[normalized_email]["active"] = True
        return {"success": True, "message": "Newsletter preferences updated"}
    
    _newsletter_subscribers[normalized_email] = {
        "email": normalized_email,
        "preferences": request.preferences,
        "subscribed_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
    }
    
    email_body = f"""
    Welcome to AI Trading Newsletter!
    
    You've been subscribed to receive updates about:
    {', '.join(request.preferences)}
    
    You can unsubscribe at any time.
    """
    
    _send_email_mock(
        to_email=request.email,
        subject="Welcome to AI Trading Newsletter",
        body=email_body
    )
    
    return {"success": True, "message": "Subscribed to newsletter"}


@router.post("/newsletter/unsubscribe")
async def unsubscribe_newsletter(email: EmailStr):
    """
    Unsubscribe from newsletter.
    """
    normalized_email = sanitize_email(email)
    
    if normalized_email in _newsletter_subscribers:
        _newsletter_subscribers[normalized_email]["active"] = False
    
    return {"success": True, "message": "Unsubscribed from newsletter"}


@router.get("/newsletter/subscribers")
async def get_newsletter_subscribers(user: dict = Depends(get_current_user)):
    """
    Get all active newsletter subscribers (admin only).
    
    Note: In production, add admin role check.
    """
    # TODO: Add admin role verification
    active_subscribers = [
        {"email": sub["email"], "preferences": sub["preferences"]}
        for sub in _newsletter_subscribers.values()
        if sub.get("active", False)
    ]
    
    return {
        "total": len(active_subscribers),
        "subscribers": active_subscribers,
    }


@router.post("/newsletter/send")
async def send_newsletter(
    subject: str,
    body: str,
    preference: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    Send newsletter to all subscribers (admin only).
    
    Note: In production, add admin role check.
    """
    # TODO: Add admin role verification
    
    recipients = [
        sub["email"]
        for sub in _newsletter_subscribers.values()
        if sub.get("active", False) and (preference is None or preference in sub.get("preferences", []))
    ]
    
    for email in recipients:
        _send_email_mock(
            to_email=email,
            subject=subject,
            body=body
        )
    
    return {
        "success": True,
        "sent_count": len(recipients),
        "recipients": recipients[:10],  # First 10 for preview
    }