"""Alerting system for critical events."""

import logging
import smtplib
import asyncio
import aiohttp
from email.mime.text import MIMEText
from typing import Optional, Dict, Any, List
from decimal import Decimal
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class NotificationProvider(ABC):
    """Base class for notification providers."""
    
    @abstractmethod
    async def send(self, message: str, title: str, priority: str = "normal") -> bool:
        """Send a notification.
        
        Args:
            message: Notification message
            title: Notification title
            priority: Priority level (low, normal, high, emergency)
            
        Returns:
            True if successful
        """
        pass


class PushoverProvider(NotificationProvider):
    """Pushover notification provider."""
    
    def __init__(self, api_key: str, user_key: str):
        """Initialize Pushover provider.
        
        Args:
            api_key: Pushover application API key
            user_key: Pushover user key
        """
        self.api_key = api_key
        self.user_key = user_key
        self.api_url = "https://api.pushover.net/1/messages.json"
    
    async def send(self, message: str, title: str, priority: str = "normal") -> bool:
        """Send Pushover notification.
        
        Args:
            message: Notification message
            title: Notification title
            priority: Priority level (0=low, 1=normal, 2=high, 2=emergency)
            
        Returns:
            True if successful
        """
        priority_map = {
            "low": -1,
            "normal": 0,
            "high": 1,
            "emergency": 2
        }
        priority_num = priority_map.get(priority, 0)
        
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "token": self.api_key,
                    "user": self.user_key,
                    "message": message,
                    "title": title,
                    "priority": priority_num
                }
                async with session.post(self.api_url, data=data) as response:
                    if response.status == 200:
                        logger.info(f"Pushover notification sent: {title}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Pushover API error: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error sending Pushover notification: {e}")
            return False


class TwilioProvider(NotificationProvider):
    """Twilio SMS notification provider."""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str, to_number: str):
        """Initialize Twilio provider.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            from_number: Twilio phone number to send from
            to_number: Phone number to send to
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_number = to_number
        self.api_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    
    async def send(self, message: str, title: str, priority: str = "normal") -> bool:
        """Send Twilio SMS.
        
        Args:
            message: SMS message (title + message combined)
            title: Message title (prepended to message)
            priority: Ignored for SMS
            
        Returns:
            True if successful
        """
        full_message = f"{title}: {message}"
        
        try:
            import aiohttp
            import base64
            
            # Basic auth
            auth_string = f"{self.account_sid}:{self.auth_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            
            async with aiohttp.ClientSession() as session:
                data = {
                    "From": self.from_number,
                    "To": self.to_number,
                    "Body": full_message
                }
                headers = {
                    "Authorization": f"Basic {auth_b64}"
                }
                async with session.post(self.api_url, data=data, headers=headers) as response:
                    if response.status in [200, 201]:
                        logger.info(f"Twilio SMS sent: {title}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Twilio API error: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error sending Twilio SMS: {e}")
            return False


class AlertingSystem:
    """System for sending alerts on critical events."""
    
    def __init__(
        self,
        enabled: bool = False,
        email: Optional[str] = None,
        pushover_api_key: Optional[str] = None,
        pushover_user_key: Optional[str] = None,
        twilio_account_sid: Optional[str] = None,
        twilio_auth_token: Optional[str] = None,
        twilio_from_number: Optional[str] = None,
        twilio_to_number: Optional[str] = None
    ):
        """Initialize alerting system.
        
        Args:
            enabled: Whether alerts are enabled
            email: Email address for alerts (if using email)
            pushover_api_key: Pushover API key
            pushover_user_key: Pushover user key
            twilio_account_sid: Twilio account SID
            twilio_auth_token: Twilio auth token
            twilio_from_number: Twilio from number
            twilio_to_number: Twilio to number
        """
        self.enabled = enabled
        self.email = email
        
        # Initialize notification providers
        self.providers: List[NotificationProvider] = []
        
        if pushover_api_key and pushover_user_key:
            self.providers.append(PushoverProvider(pushover_api_key, pushover_user_key))
            logger.info("Pushover notifications enabled")
        
        if all([twilio_account_sid, twilio_auth_token, twilio_from_number, twilio_to_number]):
            self.providers.append(TwilioProvider(
                twilio_account_sid,
                twilio_auth_token,
                twilio_from_number,
                twilio_to_number
            ))
            logger.info("Twilio SMS notifications enabled")
        
        # Event thresholds
        self.pnl_threshold = Decimal('1000')  # Alert on PnL changes > $1000
        self.drawdown_threshold = Decimal('0.05')  # Alert on drawdown > 5%
        self.mev_profit_threshold = Decimal('500')  # Alert on MEV profit > $500
        
        # Event bus subscription (will be set up separately)
        self._event_subscription = None
        
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

