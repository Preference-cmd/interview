import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO"):
    """Configure structured logging for the application."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Reduce noise from third-party libraries
    for logger_name in ["uvicorn.access", "sqlalchemy.engine"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
