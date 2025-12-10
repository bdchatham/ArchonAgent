"""Structured logging utilities for Archon system."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from functools import wraps
import time


class StructuredLogger:
    """
    Structured logger that outputs JSON-formatted logs for CloudWatch.
    
    Provides consistent logging format across all Lambda functions with:
    - Timestamp in ISO format
    - Log level
    - Component name
    - Message
    - Additional context fields
    - Request ID tracking
    """
    
    def __init__(self, name: str, level: int = logging.INFO):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically module name)
            level: Logging level (default: INFO)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Add JSON formatter handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        self.logger.addHandler(handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
        
        self.component = name
        self.request_id: Optional[str] = None
    
    def set_request_id(self, request_id: str) -> None:
        """Set request ID for correlation."""
        self.request_id = request_id
    
    def _log(
        self,
        level: int,
        message: str,
        **kwargs: Any
    ) -> None:
        """
        Internal logging method with structured context.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional context fields
        """
        extra = {
            'component': self.component,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
        
        if self.request_id:
            extra['request_id'] = self.request_id
        
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON-formatted log string
        """
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name
        }
        
        # Add extra fields from record
        if hasattr(record, 'component'):
            log_data['component'] = record.component
        
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        # Add any additional fields from extra parameter
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'message', 'pathname', 'process', 'processName',
                          'relativeCreated', 'thread', 'threadName', 'exc_info',
                          'exc_text', 'stack_info', 'component', 'request_id', 'timestamp']:
                log_data[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def log_execution_time(logger: StructuredLogger):
    """
    Decorator to log function execution time.
    
    Args:
        logger: StructuredLogger instance
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            function_name = func.__name__
            
            logger.debug(
                f"Starting {function_name}",
                function=function_name,
                event_type="function_start"
            )
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(
                    f"Completed {function_name}",
                    function=function_name,
                    execution_time_seconds=execution_time,
                    event_type="function_complete"
                )
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                logger.error(
                    f"Failed {function_name}: {str(e)}",
                    function=function_name,
                    execution_time_seconds=execution_time,
                    error=str(e),
                    error_type=type(e).__name__,
                    event_type="function_error"
                )
                raise
        
        return wrapper
    return decorator


def get_logger(name: str) -> StructuredLogger:
    """
    Get or create a structured logger.
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger instance
    """
    level_name = os.environ.get('LOG_LEVEL', 'INFO')
    level = getattr(logging, level_name, logging.INFO)
    return StructuredLogger(name, level)
