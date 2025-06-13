import logging
import sys
from typing import Callable, TypeVar, Any, Union
from functools import wraps
import requests
from pydantic import ValidationError

# Type variable for generic function signatures
F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


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
