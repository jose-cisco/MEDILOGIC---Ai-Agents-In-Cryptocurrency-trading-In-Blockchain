"""
Security Utilities for Authentication and Authorization
=========================================================

This module provides production-grade security utilities:
- JWT token generation and verification (using PyJWT)
- Password hashing and verification (using argon2/bcrypt)
- Rate limiting for authentication endpoints
- Account lockout after failed attempts
- Breach password checking (haveibeenpwned API)
- TOTP-based two-factor authentication
- Input sanitization for logging
"""
from __future__ import annotations

import hashlib
import logging
import re
import secrets
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

# ─── Rate Limiting & Account Lockout ─────────────────────────────────────────

# In-memory stores (replace with Redis in production)
_failed_attempts: dict[str, list[float]] = defaultdict(list)
_locked_accounts: dict[str, float] = {}
_rate_limits: dict[str, list[float]] = defaultdict(list)


@dataclass
class SecurityConfig:
    """Security configuration from settings."""
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 15
    rate_limit_per_minute: int = 60
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    breach_check_enabled: bool = True


def get_security_config() -> SecurityConfig:
    """Get security configuration from settings."""
    try:
        from app.core.config import get_settings
        settings = get_settings()
        return SecurityConfig(
            max_failed_attempts=getattr(settings, 'RATE_LIMIT_LOGIN_ATTEMPTS', 5),
            lockout_duration_minutes=getattr(settings, 'RATE_LIMIT_LOCKOUT_MINUTES', 15),
            rate_limit_per_minute=getattr(settings, 'RATE_LIMIT_REQUESTS_PER_MINUTE', 60),
            jwt_secret=getattr(settings, 'JWT_SECRET', '') or secrets.token_hex(32),
            jwt_algorithm=getattr(settings, 'JWT_ALGORITHM', 'HS256'),
            jwt_expiration_hours=getattr(settings, 'JWT_EXPIRATION_HOURS', 24),
            breach_check_enabled=getattr(settings, 'PASSWORD_BREACH_CHECK_ENABLED', True),
        )
    except Exception:
        return SecurityConfig()


def check_rate_limit(identifier: str, max_requests: Optional[int] = None) -> tuple[bool, int]:
    """
    Check if an identifier has exceeded rate limit.
    
    Args:
        identifier: IP address or user identifier
        max_requests: Maximum requests per minute (default from config)
    
    Returns:
        Tuple of (allowed: bool, remaining: int)
    """
    config = get_security_config()
    max_req = max_requests or config.rate_limit_per_minute
    
    now = time.time()
    window = _rate_limits[identifier]
    
    # Remove requests older than 1 minute
    window[:] = [t for t in window if now - t < 60]
    
    if len(window) >= max_req:
        return False, 0
    
    window.append(now)
    return True, max_req - len(window)


def record_failed_login(email: str) -> tuple[bool, int]:
    """
    Record a failed login attempt and check if account should be locked.
    
    Args:
        email: User email address
    
    Returns:
        Tuple of (is_locked: bool, attempts_remaining: int)
    """
    config = get_security_config()
    
    # Check if already locked
    if email in _locked_accounts:
        lockout_end = _locked_accounts[email]
        if time.time() < lockout_end:
            return True, 0
        else:
            # Lockout expired, clear it
            del _locked_accounts[email]
    
    # Record failed attempt
    _failed_attempts[email].append(time.time())
    
    # Count recent failures within lockout window
    window_start = time.time() - (config.lockout_duration_minutes * 60)
    recent_failures = [t for t in _failed_attempts[email] if t > window_start]
    _failed_attempts[email] = recent_failures
    
    attempts_remaining = config.max_failed_attempts - len(recent_failures)
    
    # Lock account if threshold exceeded
    if attempts_remaining <= 0:
        _locked_accounts[email] = time.time() + (config.lockout_duration_minutes * 60)
        logger.warning(
            "Account locked due to failed login attempts",
            extra={"email": email, "lockout_minutes": config.lockout_duration_minutes}
        )
        return True, 0
    
    return False, attempts_remaining


def clear_failed_logins(email: str) -> None:
    """Clear failed login attempts after successful login."""
    _failed_attempts.pop(email, None)
    _locked_accounts.pop(email, None)


def is_account_locked(email: str) -> tuple[bool, Optional[int]]:
    """
    Check if an account is currently locked.
    
    Returns:
        Tuple of (is_locked: bool, seconds_remaining: Optional[int])
    """
    if email not in _locked_accounts:
        return False, None
    
    lockout_end = _locked_accounts[email]
    now = time.time()
    
    if now >= lockout_end:
        # Lockout expired
        del _locked_accounts[email]
        _failed_attempts.pop(email, None)
        return False, None
    
    remaining = int(lockout_end - now)
    return True, remaining


# ─── Password Security ─────────────────────────────────────────────────────

def hash_password(password: str) -> tuple[str, str]:
    """
    Hash a password using Argon2 (preferred) or bcrypt.
    
    Returns:
        Tuple of (hashed_password: str, salt: str)
    """
    try:
        # Try Argon2 first (most secure)
        import argon2
        hasher = argon2.PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16
        )
        # Argon2 includes salt in hash
        hashed = hasher.hash(password)
        return hashed, ""
    except ImportError:
        pass
    
    try:
        # Fallback to bcrypt
        import bcrypt
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8'), salt.decode('utf-8')
    except ImportError:
        pass
    
    # Fallback to PBKDF2-HMAC-SHA256 (least secure but always available)
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 250000)
    return hashed.hex(), salt


def verify_password(password: str, hashed: str, salt: str = "") -> bool:
    """
    Verify a password against a hash using timing-safe comparison.
    
    Args:
        password: Plain text password
        hashed: Hashed password
        salt: Salt (empty for Argon2/bcrypt which include it)
    
    Returns:
        True if password matches
    """
    try:
        # Try Argon2 first
        import argon2
        hasher = argon2.PasswordHasher()
        try:
            hasher.verify(hashed, password)
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False
        except Exception:
            pass
    except ImportError:
        pass
    
    try:
        # Try bcrypt
        import bcrypt
        if not salt:  # bcrypt includes salt in hash
            try:
                return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            except Exception:
                pass
    except ImportError:
        pass
    
    # Fallback to PBKDF2
    if salt:
        new_hash, _ = hash_password_pbkdf2(password, salt)
        return secrets.compare_digest(hashed, new_hash)
    
    return False


def hash_password_pbkdf2(password: str, salt: str) -> tuple[str, str]:
    """Hash password using PBKDF2-HMAC-SHA256 (fallback)."""
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 250000)
    return hashed.hex(), salt


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password meets security requirements.
    
    Returns:
        Tuple of (is_valid: bool, errors: list[str])
    """
    config = get_security_config()
    errors = []
    
    try:
        from app.core.config import get_settings
        settings = get_settings()
        min_length = getattr(settings, 'PASSWORD_MIN_LENGTH', 8)
        require_upper = getattr(settings, 'PASSWORD_REQUIRE_UPPERCASE', True)
        require_lower = getattr(settings, 'PASSWORD_REQUIRE_LOWERCASE', True)
        require_number = getattr(settings, 'PASSWORD_REQUIRE_NUMBER', True)
        require_special = getattr(settings, 'PASSWORD_REQUIRE_SPECIAL', False)
    except Exception:
        min_length = 8
        require_upper = True
        require_lower = True
        require_number = True
        require_special = False
    
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters")
    
    if require_upper and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    if require_lower and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    if require_number and not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one number")
    
    if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    return len(errors) == 0, errors


# ─── Breach Password Checking ───────────────────────────────────────────────

async def check_password_breached(password: str) -> bool:
    """
    Check if password has been exposed in a data breach.
    
    Uses k-anonymity API from haveibeenpwned.com - only sends first 5 chars
    of SHA1 hash, never the full hash or password.
    
    Args:
        password: Password to check
    
    Returns:
        True if password found in breach database
    """
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if not getattr(settings, 'PASSWORD_BREACH_CHECK_ENABLED', True):
            return False
    except Exception:
        pass
    
    import httpx
    
    sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"https://api.pwnedpasswords.com/range/{prefix}")
            if resp.status_code == 200:
                # Check if suffix is in response
                for line in resp.text.split('\n'):
                    if line.strip().startswith(suffix):
                        # Password found - extract count
                        count = int(line.split(':')[1].strip())
                        logger.warning(
                            "Password found in breach database",
                            extra={"count": count, "prefix": prefix}
                        )
                        return True
    except Exception as e:
        logger.debug(f"Could not check breach status: {e}")
        # Don't fail registration if API is unreachable
        return False
    
    return False


# ─── JWT Token Management ─────────────────────────────────────────────────────

def generate_jwt(
    subject: str,
    additional_claims: Optional[dict] = None,
    expiration_hours: Optional[int] = None
) -> str:
    """
    Generate a secure JWT token using PyJWT.
    
    Args:
        subject: User identifier (typically email)
        additional_claims: Optional additional claims to include
        expiration_hours: Token expiration in hours (default from config)
    
    Returns:
        Encoded JWT token string
    """
    import jwt
    
    config = get_security_config()
    
    now = datetime.now(timezone.utc)
    exp_hours = expiration_hours or config.jwt_expiration_hours
    
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(hours=exp_hours),
        "jti": secrets.token_urlsafe(16),  # Unique token ID
        "type": "access",
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def verify_jwt(token: str) -> tuple[bool, Optional[dict], Optional[str]]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Tuple of (valid: bool, payload: Optional[dict], error: Optional[str])
    """
    import jwt
    
    config = get_security_config()
    
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algorithm],
            options={
                "require_exp": True,
                "require_iat": True,
                "verify_exp": True,
                "verify_iat": True,
            }
        )
        return True, payload, None
    except jwt.ExpiredSignatureError:
        return False, None, "Token has expired"
    except jwt.InvalidTokenError as e:
        return False, None, f"Invalid token: {str(e)}"
    except Exception as e:
        return False, None, f"Token verification failed: {str(e)}"


def decode_jwt_unsafe(token: str) -> Optional[dict]:
    """
    Decode a JWT token WITHOUT verification.
    
    WARNING: Use only for debugging or when you don't need to trust the contents.
    """
    import jwt
    try:
        # Decode without verification
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception:
        return None


# ─── Token Blacklist (for logout) ────────────────────────────────────────────

_blacklisted_tokens: dict[str, float] = {}


def blacklist_token(token: str, expiration_hours: int = 24) -> None:
    """Add a token to the blacklist."""
    # Store until expiration
    _blacklisted_tokens[token] = time.time() + (expiration_hours * 3600)
    # Clean old entries periodically
    _clean_blacklist()


def is_token_blacklisted(token: str) -> bool:
    """Check if a token has been blacklisted."""
    return token in _blacklisted_tokens


def _clean_blacklist() -> None:
    """Remove expired tokens from blacklist."""
    now = time.time()
    expired = [t for t, exp in _blacklisted_tokens.items() if exp < now]
    for token in expired:
        del _blacklisted_tokens[token]


# ─── Two-Factor Authentication (TOTP) ─────────────────────────────────────────

def generate_totp_secret() -> str:
    """Generate a new TOTP secret for authenticator apps."""
    import pyotp
    return pyotp.random_base32()


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    """
    Verify a TOTP code against a secret.
    
    Args:
        secret: TOTP secret (base32 encoded)
        code: 6-digit code from authenticator app
        valid_window: Number of time steps to accept (1 = ±30 seconds)
    
    Returns:
        True if code is valid
    """
    import pyotp
    
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=valid_window)
    except Exception:
        return False


def get_totp_uri(secret: str, email: str, issuer: str = "AI Trading Platform") -> str:
    """Generate a TOTP URI for QR code generation."""
    import pyotp
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


# ─── Input Sanitization ─────────────────────────────────────────────────────

def sanitize_for_log(value: str, max_length: int = 200) -> str:
    """
    Sanitize a string for safe logging.
    
    Removes potential log injection characters and truncates.
    """
    if not value:
        return ""
    
    sanitized = str(value)
    # Remove newlines, tabs, and control characters
    sanitized = re.sub(r'[\n\r\t\x00-\x1f]', ' ', sanitized)
    # Remove potential log injection sequences
    sanitized = re.sub(r'\x1b\[[0-9;]*m', '', sanitized)  # ANSI codes
    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized


def sanitize_email(email: str) -> str:
    """Sanitize and normalize an email address."""
    if not email:
        return ""
    return email.lower().strip()


# ─── Security Event Logging ─────────────────────────────────────────────────

class SecurityEventType:
    """Security event types for audit logging."""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    TOKEN_BLACKLISTED = "token_blacklisted"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    BREACH_PASSWORD_DETECTED = "breach_password_detected"


def log_security_event(
    event_type: str,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None
) -> None:
    """
    Log a security event for audit purposes.
    
    This should be sent to a centralized logging system in production.
    """
    log_data = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email": sanitize_email(email) if email else None,
        "ip_address": ip_address,
        "user_agent": sanitize_for_log(user_agent) if user_agent else None,
        "details": details or {}
    }
    
    # Log locally
    logger.info(
        "SECURITY_EVENT: %s",
        event_type,
        extra=log_data
    )
    
    # In production, send to centralized logging/monitoring
    # e.g., ELK stack, Datadog, CloudWatch, etc.