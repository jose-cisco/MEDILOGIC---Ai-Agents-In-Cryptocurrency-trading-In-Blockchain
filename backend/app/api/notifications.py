"""
Notifications API
=================
Handles newsletter emails and activity-based notifications.

Features:
- Newsletter sending to Gmail/Hotmail
- Activity performance notifications (trades, profits, losses)
- Account status notifications (security, verification)
- User notification preferences
- Email templates for different notification types
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import secrets

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Request/Response Models ──────────────────────────────────────────────────

class NotificationPreferences(BaseModel):
    """User notification preferences."""
    newsletter_enabled: bool = Field(default=True, description="Receive newsletter")
    trading_updates: bool = Field(default=True, description="Trading activity notifications")
    profit_alerts: bool = Field(default=True, description="Profit/loss notifications")
    security_alerts: bool = Field(default=True, description="Security and account alerts")
    system_updates: bool = Field(default=True, description="System maintenance updates")
    daily_summary: bool = Field(default=False, description="Daily activity summary")
    weekly_report: bool = Field(default=True, description="Weekly performance report")


class SendNewsletterRequest(BaseModel):
    """Newsletter send request."""
    subject: str = Field(..., description="Newsletter subject")
    content: str = Field(..., description="Newsletter content (HTML supported)")
    target_preferences: List[str] = Field(default=["newsletter_enabled"], description="Target users with these preferences")


class SendActivityNotificationRequest(BaseModel):
    """Activity notification request."""
    email: EmailStr = Field(..., description="User email")
    notification_type: str = Field(..., description="Type: 'trade', 'profit', 'loss', 'security', 'system'")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional data")


class NotificationHistoryResponse(BaseModel):
    """Notification history response."""
    notifications: List[Dict[str, Any]]
    total: int
    unread_count: int


# ─── In-Memory Storage (Replace with database in production) ─────────────

_notification_preferences = {}  # email -> preferences
_notification_history = {}  # email -> list of notifications
_email_templates = {}  # template_name -> template


# ─── Email Templates ──────────────────────────────────────────────────────

EMAIL_TEMPLATES = {
    "newsletter": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .footer {{ background: #f5f5f5; padding: 15px; text-align: center; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1 style="color: white; margin: 0;">AI Agent Trading</h1>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>You received this email because you subscribed to AI Agent Trading newsletter.</p>
            <p><a href="{{unsubscribe_url}}">Unsubscribe</a> | <a href="{{preferences_url}}">Manage Preferences</a></p>
        </div>
    </body>
    </html>
    """,
    
    "trade_notification": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
            .header {{ background: #1a1a2e; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .trade-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 10px 0; }}
            .profit {{ color: #10b981; }}
            .loss {{ color: #ef4444; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="color: white; margin: 0;">Trade Execution</h2>
        </div>
        <div class="content">
            <h3>{title}</h3>
            <p>{message}</p>
            <div class="trade-card">
                <p><strong>Trade ID:</strong> {trade_id}</p>
                <p><strong>Amount:</strong> {amount}</p>
                <p><strong>Result:</strong> <span class="{result_class}">{result}</span></p>
            </div>
        </div>
    </body>
    </html>
    """,
    
    "profit_alert": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #059669 0%, #10b981 100%); padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .profit-box {{ background: #d1fae5; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="color: white; margin: 0;">🎉 Profit Alert!</h2>
        </div>
        <div class="content">
            <h3>{title}</h3>
            <div class="profit-box">
                <h2 style="color: #059669; margin: 0;">+${profit_amount}</h2>
                <p style="color: #047857;">{profit_percentage}% gain</p>
            </div>
            <p>{message}</p>
        </div>
    </body>
    </html>
    """,
    
    "loss_alert": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%); padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .loss-box {{ background: #fee2e2; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="color: white; margin: 0;">⚠️ Loss Alert</h2>
        </div>
        <div class="content">
            <h3>{title}</h3>
            <div class="loss-box">
                <h2 style="color: #dc2626; margin: 0;">-${loss_amount}</h2>
                <p style="color: #b91c1c;">{loss_percentage}% loss</p>
            </div>
            <p>{message}</p>
            <p><em>Remember: Trading involves risk. Never invest more than you can afford to lose.</em></p>
        </div>
    </body>
    </html>
    """,
    
    "security_alert": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
            .header {{ background: #1e3a8a; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .alert-box {{ background: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; margin: 15px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="color: white; margin: 0;">🔒 Security Alert</h2>
        </div>
        <div class="content">
            <h3>{title}</h3>
            <div class="alert-box">
                <p style="margin: 0;"><strong>Activity:</strong> {activity_type}</p>
                <p style="margin: 5px 0 0 0;"><strong>Time:</strong> {timestamp}</p>
            </div>
            <p>{message}</p>
            <p><strong>If this wasn't you, please secure your account immediately.</strong></p>
        </div>
    </body>
    </html>
    """,
    
    "daily_summary": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .stats-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }}
            .stat-box {{ background: #f3f4f6; padding: 15px; border-radius: 8px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="color: white; margin: 0;">📊 Daily Trading Summary</h2>
        </div>
        <div class="content">
            <h3>{date}</h3>
            <div class="stats-grid">
                <div class="stat-box">
                    <h4 style="margin: 0; color: #6b7280;">Trades</h4>
                    <p style="font-size: 24px; font-weight: bold; margin: 5px 0;">{trade_count}</p>
                </div>
                <div class="stat-box">
                    <h4 style="margin: 0; color: #6b7280;">P&L</h4>
                    <p style="font-size: 24px; font-weight: bold; margin: 5px 0; color: {pnl_color};">{pnl}</p>
                </div>
                <div class="stat-box">
                    <h4 style="margin: 0; color: #6b7280;">Win Rate</h4>
                    <p style="font-size: 24px; font-weight: bold; margin: 5px 0;">{win_rate}%</p>
                </div>
                <div class="stat-box">
                    <h4 style="margin: 0; color: #6b7280;">Fees</h4>
                    <p style="font-size: 24px; font-weight: bold; margin: 5px 0;">${fees}</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """,
    
    "account_status": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; }}
            .header {{ background: #1a1a2e; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .status-box {{ border-radius: 8px; padding: 20px; margin: 15px 0; }}
            .verified {{ background: #d1fae5; border: 1px solid #10b981; }}
            .warning {{ background: #fef3c7; border: 1px solid #f59e0b; }}
            .error {{ background: #fee2e2; border: 1px solid #ef4444; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="color: white; margin: 0;">📋 Account Status</h2>
        </div>
        <div class="content">
            <h3>{title}</h3>
            <div class="status-box {status_class}">
                <p style="margin: 0;"><strong>Email:</strong> {email}</p>
                <p style="margin: 5px 0;"><strong>Verification:</strong> {verification_status}</p>
                <p style="margin: 5px 0;"><strong>2FA:</strong> {twofa_status}</p>
                <p style="margin: 5px 0;"><strong>Newsletter:</strong> {newsletter_status}</p>
                <p style="margin: 5px 0;"><strong>Last Login:</strong> {last_login}</p>
            </div>
            <p>{message}</p>
        </div>
    </body>
    </html>
    """
}


# ─── Helper Functions ──────────────────────────────────────────────────────

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
    logger.info(f"  To: {to_email}")
    logger.info(f"  Subject: {subject}")
    logger.info(f"  Body Preview:\n{body[:300]}...")
    logger.info("=" * 60)
    return True


def _get_user_preferences(email: str) -> NotificationPreferences:
    """Get user notification preferences."""
    prefs = _notification_preferences.get(email.lower())
    if prefs:
        return NotificationPreferences(**prefs)
    return NotificationPreferences()  # Default preferences


def _add_notification(email: str, notification: Dict[str, Any]):
    """Add notification to user's history."""
    if email.lower() not in _notification_history:
        _notification_history[email.lower()] = []
    
    notification["id"] = secrets.token_hex(8)
    notification["timestamp"] = datetime.utcnow().isoformat()
    notification["read"] = False
    
    _notification_history[email.lower()].insert(0, notification)
    
    # Keep only last 100 notifications
    if len(_notification_history[email.lower()]) > 100:
        _notification_history[email.lower()] = _notification_history[email.lower()][:100]


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/preferences")
async def get_notification_preferences(email: EmailStr):
    """
    Get notification preferences for a user.
    """
    prefs = _get_user_preferences(email)
    return prefs.dict()


@router.post("/preferences")
async def set_notification_preferences(email: EmailStr, preferences: NotificationPreferences):
    """
    Set notification preferences for a user.
    """
    _notification_preferences[email.lower()] = preferences.dict()
    
    # Send confirmation email
    body = f"""
    <h2>Notification Preferences Updated</h2>
    <p>Your notification preferences have been updated:</p>
    <ul>
        <li>Newsletter: {'Enabled' if preferences.newsletter_enabled else 'Disabled'}</li>
        <li>Trading Updates: {'Enabled' if preferences.trading_updates else 'Disabled'}</li>
        <li>Profit Alerts: {'Enabled' if preferences.profit_alerts else 'Disabled'}</li>
        <li>Security Alerts: {'Enabled' if preferences.security_alerts else 'Disabled'}</li>
        <li>Daily Summary: {'Enabled' if preferences.daily_summary else 'Disabled'}</li>
        <li>Weekly Report: {'Enabled' if preferences.weekly_report else 'Disabled'}</li>
    </ul>
    """
    
    _send_email_mock(
        to_email=email,
        subject="Notification Preferences Updated - AI Agent Trading",
        body=body
    )
    
    return {"success": True, "message": "Preferences updated", "preferences": preferences.dict()}


@router.post("/send-newsletter")
async def send_newsletter(request: SendNewsletterRequest):
    """
    Send newsletter to all subscribed users.
    
    Admin only endpoint.
    """
    # Find users with matching preferences
    recipients = []
    for email, prefs in _notification_preferences.items():
        if all(prefs.get(pref, False) for pref in request.target_preferences):
            recipients.append(email)
    
    # Also include users from auth who have newsletter_subscribed=True
    # In production, this would query the database
    
    sent_count = 0
    for email in recipients:
        template = EMAIL_TEMPLATES["newsletter"].format(
            content=request.content,
            unsubscribe_url=f"https://your-domain.com/unsubscribe?email={email}",
            preferences_url=f"https://your-domain.com/preferences?email={email}"
        )
        
        _send_email_mock(
            to_email=email,
            subject=request.subject,
            body=template
        )
        sent_count += 1
    
    return {
        "success": True,
        "sent_count": sent_count,
        "recipients_preview": recipients[:10],
    }


@router.post("/send-activity")
async def send_activity_notification(request: SendActivityNotificationRequest):
    """
    Send activity-based notification to user.
    
    Types: trade, profit, loss, security, system
    """
    prefs = _get_user_preferences(request.email)
    
    # Check if user wants this type of notification
    type_to_pref = {
        "trade": "trading_updates",
        "profit": "profit_alerts",
        "loss": "profit_alerts",
        "security": "security_alerts",
        "system": "system_updates",
    }
    
    pref_key = type_to_pref.get(request.notification_type)
    if pref_key and not getattr(prefs, pref_key, True):
        return {"success": True, "message": "User has disabled this notification type"}
    
    # Get appropriate template
    template_name = f"{request.notification_type}_alert" if request.notification_type in ["profit", "loss", "security"] else "newsletter"
    
    if request.notification_type == "profit":
        template = EMAIL_TEMPLATES["profit_alert"].format(
            title=request.title,
            message=request.message,
            profit_amount=request.data.get("profit_amount", "0.00"),
            profit_percentage=request.data.get("profit_percentage", "0.00")
        )
    elif request.notification_type == "loss":
        template = EMAIL_TEMPLATES["loss_alert"].format(
            title=request.title,
            message=request.message,
            loss_amount=request.data.get("loss_amount", "0.00"),
            loss_percentage=request.data.get("loss_percentage", "0.00")
        )
    elif request.notification_type == "security":
        template = EMAIL_TEMPLATES["security_alert"].format(
            title=request.title,
            message=request.message,
            activity_type=request.data.get("activity_type", "Unknown"),
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        )
    else:
        template = f"<h2>{request.title}</h2><p>{request.message}</p>"
        if request.data:
            template += f"<pre>{request.data}</pre>"
    
    _send_email_mock(
        to_email=request.email,
        subject=f"[AI Trading] {request.title}",
        body=template
    )
    
    # Add to notification history
    _add_notification(request.email, {
        "type": request.notification_type,
        "title": request.title,
        "message": request.message,
        "data": request.data,
    })
    
    return {"success": True, "message": "Notification sent"}


@router.post("/send-account-status")
async def send_account_status(email: EmailStr):
    """
    Send account status notification to user.
    
    Includes verification status, 2FA status, newsletter status, last login.
    """
    # In production, fetch user data from database
    # Mock data for demonstration
    user_data = {
        "email": email,
        "email_verified": True,
        "two_factor_enabled": False,
        "newsletter_subscribed": True,
        "last_login": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
    
    template = EMAIL_TEMPLATES["account_status"].format(
        title="Your Account Status",
        email=user_data["email"],
        verification_status="✅ Verified" if user_data["email_verified"] else "❌ Not Verified",
        twofa_status="✅ Enabled" if user_data["two_factor_enabled"] else "❌ Disabled",
        newsletter_status="✅ Subscribed" if user_data["newsletter_subscribed"] else "❌ Not Subscribed",
        last_login=user_data["last_login"],
        status_class="verified" if user_data["email_verified"] else "warning",
        message="Your account is in good standing. Keep your credentials secure!"
    )
    
    _send_email_mock(
        to_email=email,
        subject="Your Account Status - AI Agent Trading",
        body=template
    )
    
    return {"success": True, "message": "Account status sent"}


@router.post("/send-daily-summary")
async def send_daily_summary(email: EmailStr):
    """
    Send daily trading summary to user.
    
    Includes trades, P&L, win rate, fees.
    """
    prefs = _get_user_preferences(email)
    if not prefs.daily_summary:
        return {"success": True, "message": "User has disabled daily summaries"}
    
    # Mock trading data - in production, fetch from database
    summary_data = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "trade_count": 5,
        "pnl": "+125.50",
        "pnl_color": "#10b981",  # Green for profit
        "win_rate": 60,
        "fees": "2.50",
    }
    
    template = EMAIL_TEMPLATES["daily_summary"].format(**summary_data)
    
    _send_email_mock(
        to_email=email,
        subject=f"Daily Trading Summary - {summary_data['date']}",
        body=template
    )
    
    return {"success": True, "message": "Daily summary sent"}


@router.post("/send-weekly-report")
async def send_weekly_report(email: EmailStr):
    """
    Send weekly performance report to user.
    
    Includes total trades, total P&L, best trade, worst trade, etc.
    """
    prefs = _get_user_preferences(email)
    if not prefs.weekly_report:
        return {"success": True, "message": "User has disabled weekly reports"}
    
    # Mock weekly data
    week_start = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    week_end = datetime.utcnow().strftime("%Y-%m-%d")
    
    body = f"""
    <h2>📊 Weekly Performance Report</h2>
    <p>Period: {week_start} to {week_end}</p>
    
    <h3>Summary</h3>
    <ul>
        <li>Total Trades: 25</li>
        <li>Winning Trades: 15 (60%)</li>
        <li>Losing Trades: 10 (40%)</li>
        <li>Total P&L: +$523.75</li>
        <li>Best Trade: +$150.00</li>
        <li>Worst Trade: -$45.00</li>
        <li>Total Fees: $12.50</li>
        <li>Net Profit: +$511.25</li>
    </ul>
    
    <h3>Performance Chart</h3>
    <p>[Chart would be rendered here in production]</p>
    
    <p><em>Keep up the great trading!</em></p>
    """
    
    _send_email_mock(
        to_email=email,
        subject=f"Weekly Trading Report - {week_start} to {week_end}",
        body=body
    )
    
    return {"success": True, "message": "Weekly report sent"}


@router.get("/history")
async def get_notification_history(email: EmailStr, limit: int = 50, unread_only: bool = False):
    """
    Get notification history for a user.
    """
    notifications = _notification_history.get(email.lower(), [])
    
    if unread_only:
        notifications = [n for n in notifications if not n.get("read", False)]
    
    unread_count = sum(1 for n in _notification_history.get(email.lower(), []) if not n.get("read", False))
    
    return {
        "notifications": notifications[:limit],
        "total": len(notifications),
        "unread_count": unread_count,
    }


@router.post("/mark-read")
async def mark_notification_read(email: EmailStr, notification_id: str):
    """
    Mark a notification as read.
    """
    notifications = _notification_history.get(email.lower(), [])
    
    for notification in notifications:
        if notification.get("id") == notification_id:
            notification["read"] = True
            return {"success": True, "message": "Notification marked as read"}
    
    return {"success": False, "message": "Notification not found"}


@router.post("/mark-all-read")
async def mark_all_notifications_read(email: EmailStr):
    """
    Mark all notifications as read for a user.
    """
    notifications = _notification_history.get(email.lower(), [])
    
    for notification in notifications:
        notification["read"] = True
    
    return {"success": True, "message": f"Marked {len(notifications)} notifications as read"}


@router.delete("/clear")
async def clear_notification_history(email: EmailStr):
    """
    Clear all notifications for a user.
    """
    _notification_history[email.lower()] = []
    return {"success": True, "message": "Notification history cleared"}


# ─── Broadcast to All Users ────────────────────────────────────────────────

@router.post("/broadcast")
async def broadcast_notification(
    title: str,
    message: str,
    notification_type: str = "system",
    target_verified_only: bool = False,
):
    """
    Broadcast notification to all users.
    
    Admin only endpoint.
    """
    # In production, query all users from database
    # For now, use notification_preferences keys
    all_users = list(_notification_preferences.keys())
    
    sent_count = 0
    for email in all_users:
        prefs = _get_user_preferences(email)
        
        # Check notification type preference
        type_to_pref = {
            "system": "system_updates",
            "trading": "trading_updates",
            "newsletter": "newsletter_enabled",
        }
        
        pref_key = type_to_pref.get(notification_type)
        if pref_key and not getattr(prefs, pref_key, True):
            continue
        
        _add_notification(email, {
            "type": notification_type,
            "title": title,
            "message": message,
        })
        
        _send_email_mock(
            to_email=email,
            subject=f"[AI Trading] {title}",
            body=f"<h2>{title}</h2><p>{message}</p>"
        )
        sent_count += 1
    
    return {
        "success": True,
        "sent_count": sent_count,
        "recipients": all_users[:10],
    }