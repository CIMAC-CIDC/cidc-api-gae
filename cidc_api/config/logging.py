import logging
from typing import Optional

from .settings import IS_GUNICORN, ENV


def get_logger(name: Optional[str]) -> logging.Logger:
    """Get a configured logger with the given `name`."""
    # If the app is running in gunicorn, connect to gunicorn's loggers
    logger = logging.getLogger(name)
    if IS_GUNICORN:
        gunicorn_logger = logging.getLogger("gunicorn.error")
        logger.handlers = gunicorn_logger.handlers
        logger.setLevel(gunicorn_logger.level)
    else:
        logger.setLevel(logging.DEBUG if ENV == "dev" else logging.INFO)
    return logger
