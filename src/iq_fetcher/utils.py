import os
import sys
import logging
import requests
from typing import Callable, TypeVar, Any, Union
from functools import wraps
from pydantic import ValidationError
from pathlib import Path

# Type variable for generic function signatures
F = TypeVar("F", bound=Callable[..., Any])


# Utility: get base_dir and resolve_path
def find_project_root(start_path: str) -> str:
    """Find the project root, accommodating both development and bundled app structures."""
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).parent)

    current = Path(start_path).resolve()
    while True:
        if (current / "pyproject.toml").is_file():
            return str(current)
        parent = current.parent
        if parent == current:
            return str(Path.cwd())
        current = parent


base_dir = find_project_root(__file__)


def resolve_path(path: str) -> str:
    """Resolve relative paths to absolute paths relative to the project root."""
    p = Path(path)
    return str(p) if p.is_absolute() else str(Path(base_dir) / p)


# Terminal colors
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"


# Pretty logging with more emojis and life!
class PrettyFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        if record.levelname == "INFO":
            if "✅" in msg or "✓" in msg or "Successfully" in msg:
                return f"{Colors.GREEN}{msg}{Colors.END}"
            if "❌" in msg or "✗" in msg or "Failed" in msg:
                return f"{Colors.RED}{msg}{Colors.END}"
            if "🔍" in msg or "Found" in msg or "Fetching" in msg:
                return f"{Colors.CYAN}{Colors.BOLD}{msg}{Colors.END}"
            if "🎉" in msg or "🏆" in msg or "completed" in msg:
                return f"{Colors.PURPLE}{Colors.BOLD}{msg}{Colors.END}"
            if "🚀" in msg or "Starting" in msg or "Welcome" in msg:
                return f"{Colors.BLUE}{Colors.BOLD}{msg}{Colors.END}"
            return f"{Colors.BLUE}{msg}{Colors.END}"
        if record.levelname == "ERROR":
            return f"{Colors.RED}{Colors.BOLD}{msg}{Colors.END}"
        if record.levelname == "WARNING":
            return f"{Colors.YELLOW}{Colors.BOLD}{msg}{Colors.END}"
        return msg


# Configure logger
logger = logging.getLogger(__name__)
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
logger.setLevel(log_level)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(PrettyFormatter())
logger.addHandler(handler)
logger.propagate = False


class IQServerError(Exception):
    """Custom exception for IQ Server related errors."""

    pass


class ErrorHandler:
    """Centralized error handling with different strategies."""

    @staticmethod
    def handle_config_error(func: F) -> F:
        """Handle configuration-related errors."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except ValidationError as e:
                logger.error(f"Configuration validation failed: {e}")
                sys.exit(1)
            except FileNotFoundError as e:
                logger.error(f"Configuration file not found: {e}")
                sys.exit(1)
            except Exception as e:
                logger.error(f"Unexpected configuration error: {e}")
                sys.exit(1)

        return wrapper  # type: ignore[return-value]

    @staticmethod
    def handle_api_error(func: F) -> F:
        """Handle API-related errors with retry logic."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Union[Any, None]:
            try:
                return func(*args, **kwargs)
            except requests.exceptions.ConnectionError:
                logger.error("Failed to connect to IQ Server. Check URL and network.")
                return None
            except requests.exceptions.Timeout:
                logger.warning("Request timeout. Server may be slow.")
                return None
            except requests.exceptions.HTTPError as e:
                if e.response and e.response.status_code == 401:
                    logger.error("Authentication failed. Check credentials.")
                elif e.response and e.response.status_code == 403:
                    logger.error("Access forbidden. Check permissions.")
                elif e.response and e.response.status_code == 404:
                    logger.warning(f"Resource not found: {e}")
                else:
                    status_code = e.response.status_code if e.response else "unknown"
                    logger.error(f"HTTP error {status_code}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected API error: {e}")
                return None

        return wrapper  # type: ignore[return-value]

    @staticmethod
    def handle_file_error(func: F) -> F:
        """Handle file operation errors."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Union[Any, bool]:
            try:
                return func(*args, **kwargs)
            except PermissionError as e:
                logger.error(f"Permission denied: {e}")
                return False
            except OSError as e:
                logger.error(f"File system error: {e}")
                return False
            except Exception as e:
                logger.error(f"Unexpected file error: {e}")
                return False

        return wrapper  # type: ignore[return-value]
