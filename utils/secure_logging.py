"""Secure logging utilities to prevent sensitive data leakage."""

import logging
import re
from typing import Any, Dict, List
from decimal import Decimal


class LogSanitizer:
    """Sanitizes log messages to remove sensitive information."""
    
    # Patterns for sensitive data
    SENSITIVE_PATTERNS = [
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?([^,\s\)"\']+)', r'api_key=***REDACTED***'),
        (r'api[_-]?secret["\']?\s*[:=]\s*["\']?([^,\s\)"\']+)', r'api_secret=***REDACTED***'),
        (r'secret["\']?\s*[:=]\s*["\']?([^,\s\)"\']+)', r'secret=***REDACTED***'),
        (r'password["\']?\s*[:=]\s*["\']?([^,\s\)"\']+)', r'password=***REDACTED***'),
        (r'token["\']?\s*[:=]\s*["\']?([^,\s\)"\']+)', r'token=***REDACTED***'),
        (r'passphrase["\']?\s*[:=]\s*["\']?([^,\s\)"\']+)', r'passphrase=***REDACTED***'),
        (r'private[_-]?key["\']?\s*[:=]\s*["\']?([^,\s\)"\']+)', r'private_key=***REDACTED***'),
    ]
    
    # Attributes that should be redacted from objects
    SENSITIVE_ATTRS = [
        'api_key', 'api_secret', 'secret', 'password', 'token',
        'passphrase', 'private_key', 'apiKey', 'apiSecret'
    ]
    
    @classmethod
    def sanitize_string(cls, text: str) -> str:
        """Sanitize a string by redacting sensitive patterns.
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        sanitized = text
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize a dictionary by redacting sensitive keys.
        
        Args:
            data: Dictionary to sanitize
            
        Returns:
            Sanitized dictionary
        """
        sanitized = {}
        for key, value in data.items():
            # Check if key is sensitive
            if any(attr.lower() in key.lower() for attr in cls.SENSITIVE_ATTRS):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value)
            elif isinstance(value, str):
                sanitized[key] = cls.sanitize_string(value)
            else:
                sanitized[key] = value
        return sanitized
    
    @classmethod
    def format_exception(cls, exc: Exception) -> str:
        """Format exception for logging without sensitive data.
        
        Args:
            exc: Exception to format
            
        Returns:
            Sanitized exception string
        """
        import traceback
        
        # Get traceback
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        
        # Sanitize each line
        sanitized_lines = []
        for line in tb_lines:
            sanitized_line = cls.sanitize_string(line)
            sanitized_lines.append(sanitized_line)
        
        return ''.join(sanitized_lines)
    
    @classmethod
    def sanitize_object(cls, obj: Any) -> Any:
        """Sanitize an object by redacting sensitive attributes.
        
        Args:
            obj: Object to sanitize
            
        Returns:
            Sanitized representation
        """
        if isinstance(obj, dict):
            return cls.sanitize_dict(obj)
        elif isinstance(obj, str):
            return cls.sanitize_string(obj)
        elif hasattr(obj, '__dict__'):
            # Object with attributes
            sanitized = {}
            for attr, value in obj.__dict__.items():
                if any(sensitive in attr.lower() for sensitive in cls.SENSITIVE_ATTRS):
                    sanitized[attr] = "***REDACTED***"
                else:
                    sanitized[attr] = cls.sanitize_object(value)
            return sanitized
        else:
            return obj


class SecureFormatter(logging.Formatter):
    """Log formatter that automatically sanitizes sensitive data."""
    
    def __init__(self, *args, **kwargs):
        """Initialize secure formatter."""
        super().__init__(*args, **kwargs)
        self.sanitizer = LogSanitizer()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sanitization.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted and sanitized log message
        """
        # Sanitize message
        if isinstance(record.msg, str):
            record.msg = self.sanitizer.sanitize_string(record.msg)
        elif isinstance(record.msg, dict):
            record.msg = self.sanitizer.sanitize_dict(record.msg)
        
        # Sanitize args
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, (str, dict)):
                    sanitized_args.append(self.sanitizer.sanitize_object(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        # Format exception if present
        if record.exc_info:
            # Replace exception text with sanitized version
            exc_text = self.sanitizer.format_exception(record.exc_info[1])
            # Store original exc_info
            original_exc_info = record.exc_info
            record.exc_info = None
            record.exc_text = exc_text
        
        formatted = super().format(record)
        
        # Restore exc_info for proper exception formatting if needed
        if hasattr(record, 'exc_text'):
            delattr(record, 'exc_text')
            record.exc_info = original_exc_info
        
        return formatted

