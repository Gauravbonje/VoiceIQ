import sys
from loguru import logger
from app.core.config import settings


def setup_logging():
    logger.remove()

    # Console logs
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
        level=settings.log_level,
        colorize=True,
    )

    # File logs
    logger.add(
        "logs/voiceiq.log",
        rotation="20 MB",
        retention="14 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )

    return logger


log = setup_logging()