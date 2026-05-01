"""
Centralized Logging and Alerting Configuration
==============================================

Production-grade logging with:
- Structured JSON logging
- Centralized log aggregation support
- Security event alerting
- Log rotation
- Multiple output handlers (console, file, external)
- Real-time alerting for critical events
"""
from __future__ import annotations

import logging
import json
import sys
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, field
from enum import Enum
import threading
import queue


class LogLevel(str, Enum):
    """Log levels with severity."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    pattern: str
    severity: AlertSeverity
    count_threshold: int = 1
    time_window_seconds: int = 60
    enabled: bool = True
    cooldown_seconds: int = 300


@dataclass
class Alert:
    """Alert data structure."""
    rule_name: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: str
    count: int = 1


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        if self.include_extra:
            extra_fields = {}
            reserved_fields = {
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'pathname', 'process', 'processName', 'relativeCreated',
                'stack_info', 'exc_info', 'exc_text', 'message', 'asctime'
            }
            for key, value in record.__dict__.items():
                if key not in reserved_fields:
                    try:
                        json.dumps({key: value})
                        extra_fields[key] = value
                    except (TypeError, ValueError):
                        extra_fields[key] = str(value)
            
            if extra_fields:
                log_data["extra"] = extra_fields
        
        return json.dumps(log_data)


class SecurityLogFilter(logging.Filter):
    """Filter to identify and tag security-related log messages."""
    
    SECURITY_PATTERNS = [
        "login", "password", "auth", "token", "session", "api_key",
        "permission", "access", "forbidden", "unauthorized", "blocked",
        "rate_limit", "lockout", "breach", "injection", "xss", "csrf",
        "security", "attack", "exploit", "vulnerability"
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Tag security-related logs."""
        message_lower = record.getMessage().lower()
        is_security = any(pattern in message_lower for pattern in self.SECURITY_PATTERNS)
        record.is_security = is_security
        return True


class AlertManager:
    """Manages alert rules and triggers notifications."""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.alert_counts: Dict[str, list] = {}
        self.last_alert_time: Dict[str, float] = {}
        self.alert_handlers: list[Callable] = []
        self._lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self.rules[rule.name] = rule
    
    def add_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler function."""
        self.alert_handlers.append(handler)
    
    def check_and_alert(self, record: logging.LogRecord) -> Optional[Alert]:
        """Check if a log record matches any alert rules."""
        message = record.getMessage()
        current_time = datetime.now(timezone.utc).timestamp()
        
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            if rule.pattern.lower() in message.lower():
                with self._lock:
                    if rule_name not in self.alert_counts:
                        self.alert_counts[rule_name] = []
                    
                    self.alert_counts[rule_name].append(current_time)
                    
                    self.alert_counts[rule_name] = [
                        t for t in self.alert_counts[rule_name]
                        if current_time - t <= rule.time_window_seconds
                    ]
                    
                    count = len(self.alert_counts[rule_name])
                    last_alert = self.last_alert_time.get(rule_name, 0)
                    cooldown_passed = (current_time - last_alert) >= rule.cooldown_seconds
                    
                    if count >= rule.count_threshold and cooldown_passed:
                        self.last_alert_time[rule_name] = current_time
                        
                        alert = Alert(
                            rule_name=rule_name,
                            severity=rule.severity,
                            message=message,
                            details={
                                "count": count,
                                "time_window_seconds": rule.time_window_seconds,
                                "logger": record.name,
                                "level": record.levelname,
                            },
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            count=count,
                        )
                        
                        self._queue.put(alert)
                        return alert
        
        return None
    
    def process_alerts(self) -> None:
        """Process queued alerts (run in background thread)."""
        while self._running:
            try:
                alert = self._queue.get(timeout=1.0)
                self._dispatch_alert(alert)
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Error processing alert: {e}")
    
    def _dispatch_alert(self, alert: Alert) -> None:
        """Dispatch alert to all registered handlers."""
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logging.error(f"Alert handler error: {e}")
    
    def start(self) -> None:
        """Start the alert processing thread."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._running = True
            self._worker_thread = threading.Thread(target=self.process_alerts, daemon=True)
            self._worker_thread.start()
    
    def stop(self) -> None:
        """Stop the alert processing thread."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)


# ─── Alert Handlers ──────────────────────────────────────────────────────────

def webhook_alert_handler(webhook_url: str) -> Callable[[Alert], None]:
    """Create a webhook alert handler."""
    def handler(alert: Alert) -> None:
        import httpx
        
        payload = {
            "text": f"🚨 [{alert.severity.value.upper()}] {alert.rule_name}",
            "details": {
                "message": alert.message,
                "severity": alert.severity.value,
                "count": alert.count,
                "timestamp": alert.timestamp,
                **alert.details
            }
        }
        
        try:
            httpx.post(webhook_url, json=payload, timeout=5.0)
        except Exception as e:
            logging.error(f"Webhook alert failed: {e}")
    
    return handler


def console_alert_handler(alert: Alert) -> None:
    """Print alert to console with formatting."""
    severity_colors = {
        AlertSeverity.LOW: "\033[94m",
        AlertSeverity.MEDIUM: "\033[93m",
        AlertSeverity.HIGH: "\033[91m",
        AlertSeverity.CRITICAL: "\033[95m",
    }
    reset_color = "\033[0m"
    
    color = severity_colors.get(alert.severity, "")
    print(f"{color}🚨 [{alert.severity.value.upper()}] {alert.rule_name}: {alert.message}{reset_color}")


# ─── Logging Setup ────────────────────────────────────────────────────────────

_alert_manager: Optional[AlertManager] = None


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_file_size: int = 100 * 1024 * 1024,
    backup_count: int = 10,
    json_format: bool = True,
    enable_alerts: bool = True,
    alert_webhook_url: Optional[str] = None,
) -> logging.Logger:
    """Set up centralized logging with optional alerting."""
    global _alert_manager
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SecurityLogFilter())
    root_logger.addHandler(console_handler)
    
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SecurityLogFilter())
        root_logger.addHandler(file_handler)
    
    if enable_alerts:
        _alert_manager = AlertManager()
        
        _alert_manager.add_rule(AlertRule(
            name="account_locked",
            pattern="account locked",
            severity=AlertSeverity.HIGH,
            count_threshold=3,
            time_window_seconds=300,
            cooldown_seconds=600,
        ))
        
        _alert_manager.add_rule(AlertRule(
            name="multiple_failed_logins",
            pattern="failed login",
            severity=AlertSeverity.MEDIUM,
            count_threshold=5,
            time_window_seconds=300,
            cooldown_seconds=300,
        ))
        
        _alert_manager.add_rule(AlertRule(
            name="rate_limit_exceeded",
            pattern="rate limit exceeded",
            severity=AlertSeverity.MEDIUM,
            count_threshold=10,
            time_window_seconds=60,
            cooldown_seconds=300,
        ))
        
        _alert_manager.add_rule(AlertRule(
            name="breach_password_detected",
            pattern="breach password detected",
            severity=AlertSeverity.HIGH,
            count_threshold=1,
            time_window_seconds=60,
            cooldown_seconds=600,
        ))
        
        _alert_manager.add_rule(AlertRule(
            name="critical_error",
            pattern="CRITICAL",
            severity=AlertSeverity.CRITICAL,
            count_threshold=1,
            time_window_seconds=60,
            cooldown_seconds=300,
        ))
        
        _alert_manager.add_handler(console_alert_handler)
        
        if alert_webhook_url:
            _alert_manager.add_handler(webhook_alert_handler(alert_webhook_url))
        
        _alert_manager.start()
    
    return root_logger


class SecurityLogger:
    """Security-focused logger that automatically triggers alerts."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_security_event(
        self,
        event_type: str,
        message: str,
        level: str = "INFO",
        details: Optional[Dict[str, Any]] = None,
        severity: AlertSeverity = AlertSeverity.LOW,
    ) -> None:
        """Log a security event with automatic alerting."""
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        
        extra = {
            "event_type": event_type,
            "security_event": True,
            "severity": severity.value,
            **(details or {})
        }
        
        log_method(f"[SECURITY] {event_type}: {message}", extra=extra)
        
        global _alert_manager
        if _alert_manager:
            record = logging.LogRecord(
                name=self.logger.name,
                level=getattr(logging, level.upper()),
                pathname="",
                lineno=0,
                msg=f"{event_type}: {message}",
                args=(),
                exc_info=None
            )
            _alert_manager.check_and_alert(record)
    
    def login_success(self, email: str, ip: str, **kwargs) -> None:
        """Log successful login."""
        self.log_security_event(
            "login_success",
            "User logged in successfully",
            level="INFO",
            details={"email": email, "ip": ip, **kwargs}
        )
    
    def login_failure(self, email: str, ip: str, reason: str, **kwargs) -> None:
        """Log failed login attempt."""
        self.log_security_event(
            "login_failure",
            f"Failed login attempt: {reason}",
            level="WARNING",
            severity=AlertSeverity.MEDIUM,
            details={"email": email, "ip": ip, "reason": reason, **kwargs}
        )
    
    def account_locked(self, email: str, ip: str, reason: str, **kwargs) -> None:
        """Log account lockout."""
        self.log_security_event(
            "account_locked",
            f"Account locked: {reason}",
            level="WARNING",
            severity=AlertSeverity.HIGH,
            details={"email": email, "ip": ip, "reason": reason, **kwargs}
        )
    
    def rate_limit_exceeded(self, identifier: str, endpoint: str, **kwargs) -> None:
        """Log rate limit exceeded."""
        self.log_security_event(
            "rate_limit_exceeded",
            f"Rate limit exceeded on {endpoint}",
            level="WARNING",
            severity=AlertSeverity.MEDIUM,
            details={"identifier": identifier, "endpoint": endpoint, **kwargs}
        )
    
    def critical_error(self, component: str, error: str, **kwargs) -> None:
        """Log critical error requiring immediate attention."""
        self.log_security_event(
            "critical_error",
            f"Critical error in {component}: {error}",
            level="CRITICAL",
            severity=AlertSeverity.CRITICAL,
            details={"component": component, "error": error, **kwargs}
        )


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return logging.getLogger(name)


def get_security_logger(name: str) -> SecurityLogger:
    """Get a security logger instance."""
    return SecurityLogger(name)


def shutdown_logging() -> None:
    """Shutdown logging and alert manager."""
    global _alert_manager
    if _alert_manager:
        _alert_manager.stop()
    logging.shutdown()