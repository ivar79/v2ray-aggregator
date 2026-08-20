"""
Logging configuration for V2Ray Aggregator.

Provides structured logging with appropriate levels and formatting.
Ensures sensitive information is never logged.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

from app.config import get_settings


def setup_logging(log_level: Optional[str] = None, log_file: Optional[str] = None) -> None:
    """
    Configure application logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file. If None, logs to stdout only.
    """
    settings = get_settings()
    
    # Determine log level
    level = log_level or settings.log_level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logs directory if logging to file
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Define log format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(log_format, date_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific log levels for noisy libraries
    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class SensitiveDataFilter(logging.Filter):
    """
    Filter to prevent sensitive data from being logged.
    
    This filter checks log messages for common sensitive patterns
    and redacts them before logging.
    """
    
    SENSITIVE_PATTERNS = [
        ('api_hash=', '***REDACTED***'),
        ('bot_token=', '***REDACTED***'),
        ('github_token=', '***REDACTED***'),
        ('session=', '***REDACTED***'),
        ('password=', '***REDACTED***'),
        ('secret=', '***REDACTED***'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to redact sensitive information.
        
        Args:
            record: Log record to filter
            
        Returns:
            True if record should be logged, False otherwise
        """
        import re
        
        if record.args:
            # Redact sensitive data in args
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    redacted = arg
                    # Use regex to match pattern=value and replace entire value
                    for pattern, replacement in self.SENSITIVE_PATTERNS:
                        # Match pattern followed by any non-space characters
                        redacted = re.sub(f'{pattern}\\S+', replacement, redacted)
                    new_args.append(redacted)
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)
        
        # Redact sensitive data in message
        message = record.getMessage()
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            # Match pattern followed by any non-space characters
            message = re.sub(f'{pattern}\\S+', replacement, message)
        record.msg = message
        
        return True
