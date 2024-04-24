import logging

__all__ = ["set_log_level", "create_logger"]

_loggers = []

_stream_handler = logging.StreamHandler()
_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
_stream_handler.setFormatter(_formatter)


def create_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.ERROR)
    logger.addHandler(_stream_handler)
    _loggers.append(logger)
    return logger


def set_log_level(level: int):
    for logger in _loggers:
        logger.setLevel(level)
