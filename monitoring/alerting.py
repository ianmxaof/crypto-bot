"""Alerting system for critical events."""

import logging
import smtplib
from email.mime.text import MIMEText
from typing import Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class AlertingSystem:
    """System for sending alerts on critical events."""
    
    def __init__(self, enabled: bool = False, email: Optional[str] = None):
        """Initialize alerting system.
        
        Args:
            enabled: Whether alerts are enabled
            email: Email address for alerts (if using email)
        """
        self.enabled = enabled
        self.email = email
        
    def send_alert(self, subject: str, message: str, severity: str = "warning"):
        """Send an alert.
        
        Args:
            subject: Alert subject
            message: Alert message
            severity: Alert severity (info, warning, critical)
        """
        if not self.enabled:
            return
            
        logger.log(
            logging.CRITICAL if severity == "critical" else
            logging.WARNING if severity == "warning" else
            logging.INFO,
            f"ALERT [{severity.upper()}]: {subject} - {message}"
        )
        
        # Email alerts (if configured)
        if self.email:
            try:
                self._send_email(subject, message)
            except Exception as e:
                logger.error(f"Failed to send email alert: {e}")
                
    def _send_email(self, subject: str, message: str):
        """Send email alert (placeholder implementation).
        
        Args:
            subject: Email subject
            message: Email message
        """
        # Placeholder - would need SMTP configuration
        # In production, use SendGrid, AWS SES, or similar
        logger.info(f"Email alert would be sent to {self.email}: {subject}")
        
    def alert_circuit_breaker(self, reason: str):
        """Alert on circuit breaker trigger.
        
        Args:
            reason: Reason for circuit breaker
        """
        self.send_alert(
            "Circuit Breaker Triggered",
            f"Trading halted: {reason}",
            severity="critical"
        )
        
    def alert_position_mismatch(self, details: str):
        """Alert on position mismatch.
        
        Args:
            details: Mismatch details
        """
        self.send_alert(
            "Position Mismatch Detected",
            f"Position reconciliation failed: {details}",
            severity="critical"
        )
        
    def alert_daily_loss_limit(self, loss: Decimal, limit: Decimal):
        """Alert on daily loss limit.
        
        Args:
            loss: Current daily loss
            limit: Loss limit
        """
        self.send_alert(
            "Daily Loss Limit Exceeded",
            f"Daily loss ${loss:,.2f} exceeds limit ${limit:,.2f}",
            severity="warning"
        )

