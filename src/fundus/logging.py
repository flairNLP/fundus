import logging
from typing import Dict

__all__ = ["set_log_level", "add_handler", "create_logger", "loggers"]

loggers: Dict[str, logging.Logger] = {}

_stream_handler = logging.StreamHandler()
_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
_stream_handler.setFormatter(_formatter)


def create_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.ERROR)
    logger.addHandler(_stream_handler)
    loggers[name] = logger
    return logger


def set_log_level(level: int):
    for logger in loggers.values():
        logger.setLevel(level)


def add_handler(handler: logging.Handler):
    for logger in loggers.values():
        logger.addHandler(handler)
