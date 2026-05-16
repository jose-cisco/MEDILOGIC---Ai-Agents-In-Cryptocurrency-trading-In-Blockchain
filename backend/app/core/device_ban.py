"""
Device Ban & Abuse Detection System
=====================================
Tracks and bans devices/users that are hazardous to the system.

Bans are triggered by:
  - Excessive API requests (traffic jam / DDoS)
  - Repeated failed authentication attempts
  - Repeated failed verification attempts
  - Trading abuse (rapid repeated trades, manipulation patterns)
  - Manual admin ban for any reason

Device identification uses:
  - Device fingerprint (browser-generated hash of User-Agent, screen, timezone, etc.)
  - Client-side device ID (UUID stored in localStorage)
  - IP address tracking
  - Combined fingerprint hash for cross-referencing

When a user is banned:
  - ALL their devices are blocked
  - Their email is blocked from creating new accounts
  - Their device fingerprints are blacklisted
  - Any future login from a banned device is rejected
"""
from __future__ import annotations

import hashlib
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.core.config import get_settings
from app.core.security import log_security_event, SecurityEventType

logger = logging.getLogger(__name__)


# ─── Data Models ──────────────────────────────────────────────────────────────

class BanReason(str, Enum):
    """Reasons for device/user ban."""
    DDOS_ATTACK = "ddos_attack"                # Traffic jam / DDoS
    BRUTE_FORCE = "brute_force"                # Repeated failed auth
    VERIFICATION_ABUSE = "verification_abuse"  # Repeated failed verification
    TRADING_ABUSE = "trading_abuse"            # Rapid repeated trades
    MANIPULATION = "manipulation"              # Market manipulation patterns
    FRAUD = "fraud"                            # Fraudulent activity
    ADMIN_BAN = "admin_ban"                    # Manual admin ban
    ACCOUNT_COMPROMISE = "account_compromise"  # Account takeover detected


class BanSeverity(str, Enum):
    """Ban severity levels."""
    WARNING = "warning"        # First offense — logged, not blocked
    TEMPORARY = "temporary"    # Blocked for a duration (hours)
    PERMANENT = "permanent"   # Blocked forever


@dataclass
class DeviceRecord:
    """Record of a device that has connected to the system."""
    device_id: str              # Client-generated UUID
    fingerprint_hash: str      # Browser fingerprint hash
    ip_address: str = ""
    user_agent: str = ""
    email: str = ""            # Associated user email
    first_seen: str = ""
    last_seen: str = ""
    request_count: int = 0
    flagged: bool = False
    banned: bool = False
    ban_reason: Optional[str] = None
    ban_severity: Optional[str] = None
    ban_expires: Optional[str] = None  # ISO timestamp for temporary bans
    banned_at: Optional[str] = None


@dataclass
class AbuseIncident:
    """Record of an abuse incident."""
    timestamp: str
    email: str
    device_id: str
    fingerprint_hash: str
    ip_address: str
    incident_type: str  # BanReason value
    severity: str       # BanSeverity value
    details: str = ""
    auto_detected: bool = True


# ─── In-Memory Stores ──────────────────────────────────────────────────────────

# device_id -> DeviceRecord
_device_db: dict[str, DeviceRecord] = {}

# fingerprint_hash -> list of device_ids
_fingerprint_index: dict[str, list[str]] = defaultdict(list)

# email -> list of device_ids
_email_device_index: dict[str, list[str]] = defaultdict(list)

# ip_address -> list of device_ids
_ip_device_index: dict[str, list[str]] = defaultdict(list)

# Active bans: device_id -> BanReason
_active_bans: dict[str, BanReason] = {}

# Banned emails: email -> BanReason
_banned_emails: dict[str, BanReason] = {}

# Banned fingerprints: fingerprint_hash -> BanReason
_banned_fingerprints: dict[str, BanReason] = {}

# Abuse incidents log
_abuse_incidents: list[AbuseIncident] = []


# ─── Rate Tracking (for auto-detection) ────────────────────────────────────────

# Request rate tracking: device_id -> [timestamps]
_request_timestamps: dict[str, list[float]] = defaultdict(list)

# Failed auth tracking: email -> [timestamps]
_failed_auth_timestamps: dict[str, list[float]] = defaultdict(list)

# Failed verification tracking: email -> [timestamps]
_failed_verification_timestamps: dict[str, list[float]] = defaultdict(list)

# Trade rate tracking: device_id -> [timestamps]
_trade_timestamps: dict[str, list[float]] = defaultdict(list)


# ─── Thresholds ────────────────────────────────────────────────────────────────

# Requests per minute before flagging
RATE_LIMIT_REQUESTS_PER_MINUTE = 60

# Failed auth attempts per 5 minutes before auto-ban
FAILED_AUTH_THRESHOLD = 10

# Failed verification attempts per hour before auto-ban
FAILED_VERIFICATION_THRESHOLD = 20

# Trades per minute before flagging
TRADE_RATE_LIMIT_PER_MINUTE = 30

# Window for rate calculations (seconds)
RATE_WINDOW = 60


# ─── Core Functions ────────────────────────────────────────────────────────────

def generate_fingerprint_hash(user_agent: str, screen_res: str, timezone: str,
                               platform: str, language: str) -> str:
    """Generate a device fingerprint hash from browser attributes.
    
    This creates a consistent hash from browser properties that can
    identify a device even if the client-side UUID is cleared.
    """
    raw = f"{user_agent}|{screen_res}|{timezone}|{platform}|{language}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def register_device(
    device_id: str,
    fingerprint_hash: str,
    ip_address: str = "",
    user_agent: str = "",
    email: str = "",
) -> DeviceRecord:
    """Register or update a device record.
    
    Called on every login/verification to track devices.
    """
    now = datetime.now(timezone.utc).isoformat()

    if device_id in _device_db:
        # Update existing record
        record = _device_db[device_id]
        record.last_seen = now
        record.request_count += 1
        if ip_address:
            record.ip_address = ip_address
        if email:
            record.email = email
    else:
        # Create new record
        record = DeviceRecord(
            device_id=device_id,
            fingerprint_hash=fingerprint_hash,
            ip_address=ip_address,
            user_agent=user_agent,
            email=email,
            first_seen=now,
            last_seen=now,
            request_count=1,
        )
        _device_db[device_id] = record

        # Update indexes
        _fingerprint_index[fingerprint_hash].append(device_id)
        if email:
            _email_device_index[email].append(device_id)
        if ip_address:
            _ip_device_index[ip_address].append(device_id)

    return record


def is_device_banned(device_id: str) -> bool:
    """Check if a device is banned."""
    if device_id in _active_bans:
        record = _device_db.get(device_id)
        if record and record.ban_severity == BanSeverity.TEMPORARY:
            # Check if temporary ban has expired
            if record.ban_expires:
                expires = datetime.fromisoformat(record.ban_expires)
                if datetime.now(timezone.utc) > expires:
                    # Ban expired — unban
                    unban_device(device_id)
                    return False
        return True
    return False


def is_fingerprint_banned(fingerprint_hash: str) -> bool:
    """Check if a device fingerprint is banned."""
    return fingerprint_hash in _banned_fingerprints


def is_email_banned(email: str) -> bool:
    """Check if an email is banned."""
    return email.lower().strip() in _banned_emails


def ban_device(
    device_id: str,
    reason: BanReason,
    severity: BanSeverity = BanSeverity.PERMANENT,
    duration_hours: int = 0,
    details: str = "",
    auto_detected: bool = True,
) -> bool:
    """Ban a device from the system.
    
    Args:
        device_id: The device to ban
        reason: Why the device is being banned
        severity: Warning, temporary, or permanent
        duration_hours: For temporary bans, how long (0 = permanent)
        details: Human-readable description
        auto_detected: True if auto-detected by abuse system
    
    Returns True if ban was applied.
    """
    record = _device_db.get(device_id)
    if not record:
        logger.warning("Attempted to ban unknown device: %s", device_id)
        return False

    now = datetime.now(timezone.utc)

    record.banned = True
    record.ban_reason = reason.value
    record.ban_severity = severity.value
    record.banned_at = now.isoformat()

    if severity == BanSeverity.TEMPORARY and duration_hours > 0:
        from datetime import timedelta
        record.ban_expires = (now + timedelta(hours=duration_hours)).isoformat()
    else:
        record.ban_expires = None

    # Add to active bans
    _active_bans[device_id] = reason

    # Also ban the fingerprint
    _banned_fingerprints[record.fingerprint_hash] = reason

    # Also ban the email if associated
    if record.email:
        _banned_emails[record.email.lower().strip()] = reason
        # Ban ALL devices associated with this email
        for other_device_id in _email_device_index.get(record.email.lower().strip(), []):
            if other_device_id != device_id:
                other = _device_db.get(other_device_id)
                if other and not other.banned:
                    other.banned = True
                    other.ban_reason = reason.value
                    other.ban_severity = severity.value
                    other.banned_at = now.isoformat()
                    _active_bans[other_device_id] = reason

    # Also ban all devices with same fingerprint (same physical device)
    for same_fp_device_id in _fingerprint_index.get(record.fingerprint_hash, []):
        if same_fp_device_id != device_id:
            same = _device_db.get(same_fp_device_id)
            if same and not same.banned:
                same.banned = True
                same.ban_reason = reason.value
                same.ban_severity = severity.value
                same.banned_at = now.isoformat()
                _active_bans[same_fp_device_id] = reason

    # Log the incident
    incident = AbuseIncident(
        timestamp=now.isoformat(),
        email=record.email,
        device_id=device_id,
        fingerprint_hash=record.fingerprint_hash,
        ip_address=record.ip_address,
        incident_type=reason.value,
        severity=severity.value,
        details=details or f"Device banned: {reason.value}",
        auto_detected=auto_detected,
    )
    _abuse_incidents.append(incident)

    # Security event
    log_security_event(
        SecurityEventType.LOGIN_FAILURE,
        email=record.email or "unknown",
        details={
            "action": "device_banned",
            "device_id": device_id,
            "reason": reason.value,
            "severity": severity.value,
            "auto_detected": auto_detected,
        }
    )

    logger.warning(
        "Device BANNED: %s (email: %s, fingerprint: %s, reason: %s, severity: %s, auto: %s)",
        device_id, record.email, record.fingerprint_hash[:8] + "...",
        reason.value, severity.value, auto_detected,
    )

    return True


def unban_device(device_id: str) -> bool:
    """Remove a ban from a device."""
    record = _device_db.get(device_id)
    if not record:
        return False

    record.banned = False
    record.ban_reason = None
    record.ban_severity = None
    record.ban_expires = None
    record.banned_at = None

    _active_bans.pop(device_id, None)
    _banned_fingerprints.pop(record.fingerprint_hash, None)
    if record.email:
        _banned_emails.pop(record.email.lower().strip(), None)

    logger.info("Device UNBANNED: %s", device_id)
    return True


# ─── Auto-Detection ────────────────────────────────────────────────────────────

def track_request(device_id: str) -> Optional[BanReason]:
    """Track an API request and check for rate abuse.
    
    Returns BanReason if abuse detected, None otherwise.
    """
    now = time.time()
    timestamps = _request_timestamps[device_id]

    # Clean old timestamps
    _request_timestamps[device_id] = [t for t in timestamps if now - t < RATE_WINDOW]
    _request_timestamps[device_id].append(now)

    # Check rate
    if len(_request_timestamps[device_id]) > RATE_LIMIT_REQUESTS_PER_MINUTE:
        logger.warning(
            "Rate abuse detected from device %s: %d requests in %d seconds",
            device_id, len(_request_timestamps[device_id]), RATE_WINDOW,
        )
        return BanReason.DDOS_ATTACK

    return None


def track_failed_auth(email: str) -> Optional[BanReason]:
    """Track a failed authentication attempt.
    
    Returns BanReason if brute force detected, None otherwise.
    """
    now = time.time()
    window = 300  # 5 minutes
    timestamps = _failed_auth_timestamps[email]

    _failed_auth_timestamps[email] = [t for t in timestamps if now - t < window]
    _failed_auth_timestamps[email].append(now)

    if len(_failed_auth_timestamps[email]) > FAILED_AUTH_THRESHOLD:
        logger.warning("Brute force detected for %s: %d failed auths in %d seconds",
                       email, len(_failed_auth_timestamps[email]), window)
        return BanReason.BRUTE_FORCE

    return None


def track_failed_verification(email: str) -> Optional[BanReason]:
    """Track a failed verification attempt.
    
    Returns BanReason if verification abuse detected, None otherwise.
    """
    now = time.time()
    window = 3600  # 1 hour
    timestamps = _failed_verification_timestamps[email]

    _failed_verification_timestamps[email] = [t for t in timestamps if now - t < window]
    _failed_verification_timestamps[email].append(now)

    if len(_failed_verification_timestamps[email]) > FAILED_VERIFICATION_THRESHOLD:
        logger.warning("Verification abuse detected for %s: %d failures in %d seconds",
                       email, len(_failed_verification_timestamps[email]), window)
        return BanReason.VERIFICATION_ABUSE

    return None


def track_trade(device_id: str) -> Optional[BanReason]:
    """Track a trade execution and check for trading abuse.
    
    Returns BanReason if abuse detected, None otherwise.
    """
    now = time.time()
    timestamps = _trade_timestamps[device_id]

    _trade_timestamps[device_id] = [t for t in timestamps if now - t < RATE_WINDOW]
    _trade_timestamps[device_id].append(now)

    if len(_trade_timestamps[device_id]) > TRADE_RATE_LIMIT_PER_MINUTE:
        logger.warning("Trading abuse detected from device %s: %d trades in %d seconds",
                       device_id, len(_trade_timestamps[device_id]), RATE_WINDOW)
        return BanReason.TRADING_ABUSE

    return None


def check_and_auto_ban(device_id: str, email: str = "") -> Optional[BanReason]:
    """Check all abuse signals and auto-ban if thresholds exceeded.
    
    Called by middleware on every request.
    Returns the BanReason if a ban was applied, None otherwise.
    """
    # Check request rate
    rate_abuse = track_request(device_id)
    if rate_abuse:
        ban_device(
            device_id, rate_abuse,
            severity=BanSeverity.TEMPORARY,
            duration_hours=1,
            details=f"Auto-detected: {rate_abuse.value} — rate limit exceeded",
            auto_detected=True,
        )
        return rate_abuse

    # Check if email has too many failed auths
    if email:
        auth_abuse = track_failed_auth(email)
        if auth_abuse:
            # Find device for this email
            for did in _email_device_index.get(email.lower().strip(), []):
                ban_device(
                    did, auth_abuse,
                    severity=BanSeverity.TEMPORARY,
                    duration_hours=24,
                    details=f"Auto-detected: {auth_abuse.value} — too many failed auth attempts",
                    auto_detected=True,
                )
            return auth_abuse

    return None


# ─── Query Functions ──────────────────────────────────────────────────────────

def get_device(device_id: str) -> Optional[DeviceRecord]:
    """Get a device record."""
    return _device_db.get(device_id)


def get_devices_for_email(email: str) -> list[DeviceRecord]:
    """Get all devices associated with an email."""
    device_ids = _email_device_index.get(email.lower().strip(), [])
    return [_device_db[did] for did in device_ids if did in _device_db]


def get_devices_for_fingerprint(fingerprint_hash: str) -> list[DeviceRecord]:
    """Get all devices with the same fingerprint."""
    device_ids = _fingerprint_index.get(fingerprint_hash, [])
    return [_device_db[did] for did in device_ids if did in _device_db]


def get_all_bans() -> list[dict]:
    """Get all active bans."""
    bans = []
    for device_id, reason in _active_bans.items():
        record = _device_db.get(device_id)
        if record:
            bans.append({
                "device_id": device_id,
                "email": record.email,
                "fingerprint_hash": record.fingerprint_hash[:8] + "...",
                "ip_address": record.ip_address,
                "reason": reason.value,
                "severity": record.ban_severity,
                "banned_at": record.banned_at,
                "expires": record.ban_expires,
            })
    return bans


def get_abuse_incidents(limit: int = 50) -> list[dict]:
    """Get recent abuse incidents."""
    incidents = _abuse_incidents[-limit:]
    return [
        {
            "timestamp": inc.timestamp,
            "email": inc.email,
            "device_id": inc.device_id,
            "fingerprint_hash": inc.fingerprint_hash[:8] + "...",
            "ip_address": inc.ip_address,
            "incident_type": inc.incident_type,
            "severity": inc.severity,
            "details": inc.details,
            "auto_detected": inc.auto_detected,
        }
        for inc in incidents
    ]


def check_device_access(device_id: str, fingerprint_hash: str, email: str = "") -> tuple[bool, str]:
    """Check if a device/user is allowed to access the system.
    
    Returns (allowed: bool, reason: str).
    This is the main gate that middleware calls.
    """
    # Check if device is banned
    if is_device_banned(device_id):
        record = _device_db.get(device_id)
        reason = record.ban_reason if record else "unknown"
        severity = record.ban_severity if record else "permanent"
        expires = record.ban_expires if record else None
        msg = f"Device banned: {reason} (severity: {severity})"
        if expires:
            msg += f" — expires: {expires}"
        return False, msg

    # Check if fingerprint is banned (even if device_id is new)
    if is_fingerprint_banned(fingerprint_hash):
        return False, f"Device fingerprint banned — this device has been blocked from the system"

    # Check if email is banned
    if email and is_email_banned(email):
        return False, f"Account banned — all devices associated with this account are blocked"

    return True, ""


# ─── FastAPI Middleware ─────────────────────────────────────────────────────────

async def device_ban_middleware(request: "Request", call_next):
    """FastAPI middleware that checks device bans on every request.
    
    Expects headers:
      - X-Device-ID: Client-generated device UUID
      - X-Device-Fingerprint: Browser fingerprint hash
      - X-User-Email: User email (if authenticated)
    
    If any of these are banned, returns HTTP 403.
    """
    from fastapi import Request  # noqa: F811
    from fastapi.responses import JSONResponse

    device_id = request.headers.get("X-Device-ID", "").strip()
    fingerprint_hash = request.headers.get("X-Device-Fingerprint", "").strip()
    email = request.headers.get("X-User-Email", "").strip()

    # Skip check for health/docs endpoints
    path = request.url.path
    if path in ("/docs", "/redoc", "/openapi.json", "/health", "/"):
        response = await call_next(request)
        return response

    # If no device headers, allow through (backward compatibility)
    if not device_id and not fingerprint_hash:
        response = await call_next(request)
        return response

    # Register/update device
    if device_id:
        register_device(
            device_id=device_id,
            fingerprint_hash=fingerprint_hash or "unknown",
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("User-Agent", ""),
            email=email,
        )

        # Auto-detect abuse
        abuse = check_and_auto_ban(device_id, email)
        if abuse:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        f"ACCESS BLOCKED: Your device has been temporarily banned due to "
                        f"suspicious activity ({abuse.value}). This ban will expire in 1 hour. "
                        f"If you believe this is an error, contact support."
                    ),
                    "ban_reason": abuse.value,
                    "ban_severity": "temporary",
                },
            )

        # Check if device is already banned
        allowed, reason = check_device_access(device_id, fingerprint_hash, email)
        if not allowed:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        f"ACCESS BLOCKED: This device has been banned from the system. "
                        f"Reason: {reason}. If you believe this is an error, contact support."
                    ),
                    "ban_reason": reason,
                },
            )

    response = await call_next(request)
    return response
