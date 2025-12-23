import logging
import sys
from app.core.config import settings

def setup_logging():
    """
    Configures the root logger for the application.
    """
    log_level = logging.INFO
    if settings.DEBUG:
        log_level = logging.DEBUG

    # Format: [Time] [Level] [Module] Message
    log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set specific levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)

    logger = logging.getLogger("app")
    logger.info(f"Logging initialized (Level: {logging.getLevelName(log_level)})")
