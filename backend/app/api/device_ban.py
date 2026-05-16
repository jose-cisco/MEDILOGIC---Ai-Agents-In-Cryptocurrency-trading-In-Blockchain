"""
Device Ban API
==============
Endpoints for device registration, ban management, and abuse monitoring.

Admin-only endpoints for banning/unbanning devices.
Public endpoints for checking device status.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional

from app.core.config import get_settings
from app.core.device_ban import (
    register_device,
    is_device_banned,
    is_email_banned,
    is_fingerprint_banned,
    ban_device,
    unban_device,
    get_device,
    get_devices_for_email,
    get_all_bans,
    get_abuse_incidents,
    check_device_access,
    generate_fingerprint_hash,
    BanReason,
    BanSeverity,
    track_trade,
    track_failed_auth,
    track_failed_verification,
)
from app.api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Request/Response Models ────────────────────────────────────────────────

class DeviceRegisterRequest(BaseModel):
    """Register a device with the system."""
    device_id: str = Field(..., description="Client-generated device UUID")
    fingerprint_hash: str = Field(..., description="Browser fingerprint hash")
    user_agent: str = Field("", description="Browser User-Agent")
    screen_resolution: str = Field("", description="Screen resolution (e.g. 1920x1080)")
    timezone: str = Field("", description="Browser timezone")
    platform: str = Field("", description="Browser platform")
    language: str = Field("", description="Browser language")


class DeviceStatusResponse(BaseModel):
    """Device ban status."""
    device_id: str
    banned: bool
    ban_reason: Optional[str] = None
    ban_severity: Optional[str] = None
    ban_expires: Optional[str] = None
    email_banned: bool = False
    fingerprint_banned: bool = False
    can_access: bool
    message: str = ""


class BanDeviceRequest(BaseModel):
    """Request to ban a device."""
    device_id: str = Field("", description="Device ID to ban")
    email: str = Field("", description="Email to ban (bans all devices)")
    fingerprint_hash: str = Field("", description="Fingerprint hash to ban")
    reason: str = Field(..., description="Ban reason: ddos_attack, brute_force, verification_abuse, trading_abuse, manipulation, fraud, admin_ban, account_compromise")
    severity: str = Field("permanent", description="Ban severity: warning, temporary, permanent")
    duration_hours: int = Field(0, description="Duration in hours for temporary bans")
    details: str = Field("", description="Human-readable ban details")


class UnbanDeviceRequest(BaseModel):
    """Request to unban a device."""
    device_id: str = Field(..., description="Device ID to unban")


class BanListResponse(BaseModel):
    """List of active bans."""
    bans: list
    total: int


class IncidentListResponse(BaseModel):
    """List of abuse incidents."""
    incidents: list
    total: int


# ─── Public Endpoints ────────────────────────────────────────────────────────

@router.post("/register")
async def register_device_endpoint(
    request: DeviceRegisterRequest,
    http_request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Register a device with the ban tracking system.
    
    Called by the frontend on login to register the device fingerprint.
    If the device is already banned, returns 403.
    """
    email = current_user.get("email", "")
    ip_address = http_request.client.host if http_request.client else ""

    # Generate fingerprint hash if not provided
    fp_hash = request.fingerprint_hash
    if not fp_hash and request.user_agent:
        fp_hash = generate_fingerprint_hash(
            request.user_agent,
            request.screen_resolution,
            request.timezone,
            request.platform,
            request.language,
        )

    # Check if device is already banned
    allowed, reason = check_device_access(request.device_id, fp_hash, email)
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"DEVICE BLOCKED: {reason}. This device has been banned from the system.",
        )

    # Register the device
    record = register_device(
        device_id=request.device_id,
        fingerprint_hash=fp_hash,
        ip_address=ip_address,
        user_agent=request.user_agent,
        email=email,
    )

    return {
        "registered": True,
        "device_id": record.device_id,
        "banned": record.banned,
        "message": "Device registered successfully.",
    }


@router.get("/status", response_model=DeviceStatusResponse)
async def get_device_status(
    device_id: str = "",
    fingerprint_hash: str = "",
    email: str = "",
    current_user: dict = Depends(get_current_user),
):
    """
    Check if a device or email is banned.
    
    Returns ban status and reason if banned.
    """
    user_email = current_user.get("email", email)

    device_banned = is_device_banned(device_id) if device_id else False
    email_banned = is_email_banned(user_email) if user_email else False
    fp_banned = is_fingerprint_banned(fingerprint_hash) if fingerprint_hash else False

    record = get_device(device_id) if device_id else None

    can_access = not device_banned and not email_banned and not fp_banned
    message = ""
    if device_banned:
        message = f"Device is banned: {record.ban_reason if record else 'unknown'}"
    elif email_banned:
        message = f"Account is banned — all associated devices are blocked"
    elif fp_banned:
        message = "Device fingerprint is banned — this device has been blocked"

    return DeviceStatusResponse(
        device_id=device_id,
        banned=device_banned or email_banned or fp_banned,
        ban_reason=record.ban_reason if record else None,
        ban_severity=record.ban_severity if record else None,
        ban_expires=record.ban_expires if record else None,
        email_banned=email_banned,
        fingerprint_banned=fp_banned,
        can_access=can_access,
        message=message,
    )


# ─── Admin Endpoints ────────────────────────────────────────────────────────

def _is_admin(email: str) -> bool:
    """Check if email belongs to a system admin."""
    settings = get_settings()
    creator_emails = [e.strip().lower() for e in settings.IDENTITY_CREATOR_EMAILS.split(",") if e.strip()]
    return email.lower().strip() in creator_emails


@router.post("/ban")
async def ban_device_endpoint(
    request: BanDeviceRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Ban a device, email, or fingerprint.
    
    **Admin-only endpoint.** Bans the specified device and all associated
    devices (same email, same fingerprint).
    """
    admin_email = current_user.get("email", "")
    if not _is_admin(admin_email):
        raise HTTPException(
            status_code=403,
            detail="Admin access required to ban devices.",
        )

    # Parse reason
    try:
        reason = BanReason(request.reason)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ban reason: {request.reason}. Must be one of: {[r.value for r in BanReason]}",
        )

    # Parse severity
    try:
        severity = BanSeverity(request.severity)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity: {request.severity}. Must be one of: {[s.value for s in BanSeverity]}",
        )

    banned_count = 0

    # Ban by email (bans ALL devices for that email)
    if request.email:
        devices = get_devices_for_email(request.email)
        for device in devices:
            if ban_device(
                device.device_id, reason, severity,
                duration_hours=request.duration_hours,
                details=request.details or f"Admin ban: {reason.value} for {request.email}",
                auto_detected=False,
            ):
                banned_count += 1
        if not devices:
            # No devices found — still ban the email
            from app.core.device_ban import _banned_emails
            _banned_emails[request.email.lower().strip()] = reason
            banned_count = 1

    # Ban by device ID
    elif request.device_id:
        if ban_device(
            request.device_id, reason, severity,
            duration_hours=request.duration_hours,
            details=request.details or f"Admin ban: {reason.value}",
            auto_detected=False,
        ):
            banned_count = 1

    # Ban by fingerprint
    elif request.fingerprint_hash:
        devices = get_devices_for_email(request.fingerprint_hash)
        from app.core.device_ban import _banned_fingerprints
        _banned_fingerprints[request.fingerprint_hash] = reason
        banned_count = len(devices) if devices else 1

    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide device_id, email, or fingerprint_hash to ban.",
        )

    return {
        "banned": True,
        "banned_count": banned_count,
        "reason": reason.value,
        "severity": severity.value,
        "message": f"Banned {banned_count} device(s) for: {reason.value}",
    }


@router.post("/unban")
async def unban_device_endpoint(
    request: UnbanDeviceRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Remove a ban from a device.
    
    **Admin-only endpoint.** Unbans the device and its associated email/fingerprint.
    """
    admin_email = current_user.get("email", "")
    if not _is_admin(admin_email):
        raise HTTPException(
            status_code=403,
            detail="Admin access required to unban devices.",
        )

    success = unban_device(request.device_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Device not found: {request.device_id}",
        )

    return {
        "unbanned": True,
        "device_id": request.device_id,
        "message": "Device unbanned successfully.",
    }


@router.get("/bans", response_model=BanListResponse)
async def list_bans(
    current_user: dict = Depends(get_current_user),
):
    """
    List all active bans.
    
    **Admin-only endpoint.**
    """
    admin_email = current_user.get("email", "")
    if not _is_admin(admin_email):
        raise HTTPException(
            status_code=403,
            detail="Admin access required to view bans.",
        )

    bans = get_all_bans()
    return BanListResponse(bans=bans, total=len(bans))


@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    """
    List recent abuse incidents.
    
    **Admin-only endpoint.**
    """
    admin_email = current_user.get("email", "")
    if not _is_admin(admin_email):
        raise HTTPException(
            status_code=403,
            detail="Admin access required to view incidents.",
        )

    incidents = get_abuse_incidents(limit=limit)
    return IncidentListResponse(incidents=incidents, total=len(incidents))
