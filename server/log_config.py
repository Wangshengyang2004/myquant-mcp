#!/usr/bin/env python3
"""
Enhanced logging configuration with rotation and request context

Features:
- 5-day log rotation
- IP address and user agent logging
- Separate access and audit logs
- Request context tracking via context variable
- Performance monitoring decorator
- Debug mode toggle
- Console logging for tool calls
"""
import logging
import logging.handlers
import json
import time
import functools
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Callable
import threading

# Debug mode toggle (set via environment variable)
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() in ("true", "1", "on")

# Create logs directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log files
ACCESS_LOG_FILE = LOG_DIR / "access_streamable_http.log"
AUDIT_LOG_FILE = LOG_DIR / "audit_streamable_http.jsonl"
ERROR_LOG_FILE = LOG_DIR / "error_streamable_http.log"


def suppress_mcp_sdk_logging():
    """Suppress verbose logging from MCP SDK internals.
    
    This silences messages like:
    - "Terminating session: None"
    - "Processing request of type CallToolRequest"
    """
    # Suppress MCP server internal logging
    mcp_loggers = [
        "mcp.server",
        "mcp.server.lowlevel", 
        "mcp.server.lowlevel.server",
        "mcp.server.session",
        "mcp.server.request_handlers",
    ]
    for logger_name in mcp_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)  # Only show warnings and errors
        logger.propagate = False


def setup_console_logging():
    """Setup console logging for the application.
    
    Shows tool calls and important messages to stdout.
    """
    # Main app logger for console
    console_logger = logging.getLogger("console")
    console_logger.setLevel(logging.INFO)
    console_logger.propagate = False
    
    if not console_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        # Format: timestamp | LEVEL | message
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        console_logger.addHandler(handler)
    
    return console_logger

# --- Context Variable for Request Info ---
class RequestContext:
    """Thread-local storage for request context"""
    _context = threading.local()

    @classmethod
    def set(cls, ip: str = None, user_agent: str = None, request_id: str = None,
             path: str = None, method: str = None, **kwargs):
        """Set request context"""
        cls._context.data = {
            "ip": ip,
            "user_agent": user_agent,
            "request_id": request_id,
            "path": path,
            "method": method,
            **kwargs
        }

    @classmethod
    def get(cls) -> Dict[str, Any]:
        """Get current request context"""
        return getattr(cls._context, 'data', {})

    @classmethod
    def clear(cls):
        """Clear request context"""
        if hasattr(cls._context, 'data'):
            delattr(cls._context, 'data')


# --- Custom Formatter with Request Context ---
class ContextFormatter(logging.Formatter):
    """Formatter that includes request context if available"""

    def format(self, record: logging.LogRecord) -> str:
        # Get request context
        context = RequestContext.get()

        # Add context to record
        record.ip = context.get('ip', '-')
        record.request_id = context.get('request_id', '-')
        record.path = context.get('path', '-')

        return super().format(record)


# --- Access Logger ---
def create_access_logger() -> logging.Logger:
    """Create access logger with 5-day rotation"""
    logger = logging.getLogger("access")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Don't propagate to root logger

    if not logger.handlers:
        # TimedRotatingFileHandler: 5 days rotation
        handler = logging.handlers.TimedRotatingFileHandler(
            ACCESS_LOG_FILE,
            when='midnight',
            interval=1,
            backupCount=5,
            encoding='utf-8'
        )
        handler.suffix = '%Y-%m-%d'
        handler.setFormatter(ContextFormatter(
            '%(asctime)s | %(ip)s | %(request_id)s | %(path)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(handler)

    return logger


# --- Audit Logger (JSONL format) ---
class AuditLogger:
    """Audit logger for tool calls and sensitive operations"""

    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if not self.logger.handlers:
            # TimedRotatingFileHandler: 5 days rotation
            handler = logging.handlers.TimedRotatingFileHandler(
                AUDIT_LOG_FILE,
                when='midnight',
                interval=1,
                backupCount=5,
                encoding='utf-8'
            )
            handler.suffix = '%Y-%m-%d'
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)

    def log_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        status: str,
        error: str = None,
        duration_ms: float = 0
    ):
        """Log a tool call with request context"""
        context = RequestContext.get()

        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            # Request context
            "ip": context.get('ip', '-'),
            "request_id": context.get('request_id', '-'),
        }

        # Add filtered arguments (hide sensitive data)
        if arguments:
            log_args = self._filter_sensitive_args(arguments)
            if log_args:
                entry["arguments"] = log_args

        if error:
            entry["error"] = error

        self.logger.info(json.dumps(entry, ensure_ascii=False))

    def _filter_sensitive_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Filter sensitive arguments for logging"""
        sensitive_keys = {'auth_token', 'password', 'token', 'secret', 'api_key'}
        filtered = {}
        for k, v in args.items():
            if k in sensitive_keys:
                filtered[k] = "***"
            elif isinstance(v, dict):
                filtered[k] = self._filter_sensitive_args(v)
            else:
                filtered[k] = v
        return filtered


# --- Error Logger ---
def create_error_logger() -> logging.Logger:
    """Create error logger with 5-day rotation"""
    logger = logging.getLogger("error")
    logger.setLevel(logging.ERROR)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.handlers.TimedRotatingFileHandler(
            ERROR_LOG_FILE,
            when='midnight',
            interval=1,
            backupCount=5,
            encoding='utf-8'
        )
        handler.suffix = '%Y-%m-%d'
        handler.setFormatter(ContextFormatter(
            '%(asctime)s | %(ip)s | %(request_id)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(handler)

    return logger


# --- Global instances ---
access_logger = create_access_logger()
audit_logger = AuditLogger()
error_logger = create_error_logger()
console_logger = setup_console_logging()

# Suppress MCP SDK verbose logging at module load time
suppress_mcp_sdk_logging()

# General application logger
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "app.log",
        when='midnight',
        interval=1,
        backupCount=5,
        encoding='utf-8'
    )
    handler.suffix = '%Y-%m-%d'
    handler.setFormatter(ContextFormatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)


# --- Starlette Middleware for Request Context ---
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to capture request context for logging"""

    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]

        # Get client IP (handle proxies)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            ip = forwarded_for.split(',')[0].strip()
        else:
            ip = request.client.host if request.client else 'unknown'

        # Get user agent
        user_agent = request.headers.get('User-Agent', '-')

        # Set context
        RequestContext.set(
            ip=ip,
            user_agent=user_agent,
            request_id=request_id,
            path=request.url.path,
            method=request.method
        )

        # Log access
        access_logger.info(f"{request.method} {request.url.path}")

        try:
            response = await call_next(request)
            return response
        finally:
            # Clear context
            RequestContext.clear()


# --- Convenience functions ---
def log_access(message: str):
    """Log access message"""
    access_logger.info(message)


def log_error(message: str, exc_info: bool = False):
    """Log error message"""
    error_logger.error(message, exc_info=exc_info)


def get_request_context() -> Dict[str, Any]:
    """Get current request context"""
    return RequestContext.get()


# --- Performance Monitoring ---
class PerformanceMonitor:
    """Performance monitoring for operations"""

    _logger = logging.getLogger("performance")
    _logger.setLevel(logging.DEBUG)
    _logger.propagate = False

    if not _logger.handlers:
        handler = logging.handlers.TimedRotatingFileHandler(
            LOG_DIR / "performance.log",
            when='midnight',
            interval=1,
            backupCount=5,
            encoding='utf-8'
        )
        handler.suffix = '%Y-%m-%d'
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        _logger.addHandler(handler)

    @classmethod
    def log(cls, operation: str, duration_ms: float, metadata: Dict[str, Any] = None):
        """Log a performance metric"""
        if DEBUG_MODE:
            context = RequestContext.get()
            entry = {
                "operation": operation,
                "duration_ms": round(duration_ms, 2),
                "request_id": context.get('request_id', '-'),
            }
            if metadata:
                entry.update(metadata)
            cls._logger.debug(json.dumps(entry))


def monitor_performance(operation_name: str = None):
    """Decorator to monitor function performance

    Usage:
        @monitor_performance("database_query")
        async def get_user(user_id):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                PerformanceMonitor.log(name, duration_ms)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = operation_name or f"{func.__module__}.{func.__name__}"
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                PerformanceMonitor.log(name, duration_ms)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# --- Debug helpers ---
def debug_log(message: str):
    """Log debug message only if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        logger = logging.getLogger("debug")
        logger.debug(message)


def get_debug_info() -> Dict[str, Any]:
    """Get current debug information"""
    return {
        "debug_mode": DEBUG_MODE,
        "log_dir": str(LOG_DIR),
        "log_files": {
            "access": str(ACCESS_LOG_FILE),
            "audit": str(AUDIT_LOG_FILE),
            "error": str(ERROR_LOG_FILE),
            "performance": str(LOG_DIR / "performance.log"),
        },
        "request_context": get_request_context(),
    }


# Import asyncio for the monitor decorator check
import asyncio
