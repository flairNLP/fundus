import logging
from typing import Dict, Set, cast

from fundus.utils.serialization import JSONVal

_default_handler_level = logging.ERROR

__all__ = ["set_log_level", "add_handler", "create_logger", "loggers", "handlers"]

# create std-handler
_stream_handler = logging.StreamHandler()
_stream_handler.name = "std-handler"
_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
_stream_handler.setFormatter(_formatter)
_stream_handler.setLevel(_default_handler_level)

loggers: Dict[str, logging.Logger] = {}
handlers: Dict[str, logging.Handler] = {_stream_handler.name: _stream_handler}


def create_logger(name: str) -> logging.Logger:
    """Create a new logger with as <name>.

    Per defaults the loggers' log level is set to DEBUG and the following handlers will be added
    automatically (see <handlers> for more details):

    std-handler: StreamHandler | ERROR | %(asctime)s - %(name)s - %(levelname)s - %(message)s

    Args:
        name: Reference name for the created logger.

    Returns:
        A new logger with name <name>
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    for handler in handlers.values():
        logger.addHandler(handler)
    loggers[name] = logger
    return logger


def set_log_level(level: int):
    """Set log level for all handlers.

    Args:
        level: The new log level to set
    """
    for handler in handlers.values():
        handler.setLevel(level)


def add_handler(handler: logging.Handler):
    """Add a new handler to all logger.

    Args:
        handler: The new handler to add.
    """
    if handler.name is None:
        raise ValueError(f"Handlers to add must have a name set")

    if handlers.get(handler.name) is not None:
        raise ValueError(f"Handler with name {handler.name} already exists")

    handlers[handler.name] = handler
    for logger in loggers.values():
        logger.addHandler(handler)


def get_current_config() -> JSONVal:
    """Get the current logging configuration as JSON.

    Returns:
        The current logging configuration as JSON.
    """

    formatters: Set[logging.Formatter] = cast(
        Set[logging.Formatter], {handler.formatter for handler in handlers.values()}
    )

    def get_formatter_config(formatter: logging.Formatter) -> JSONVal:
        return {"format": formatter._fmt}

    def get_handler_config(handler: logging.Handler) -> JSONVal:
        config: Dict[str, JSONVal] = {
            "level": handler.level,
            "formatter": hex(id(handler.formatter)),
            "class": handler.__class__.__module__ + "." + handler.__class__.__name__,
        }
        if isinstance(handler, logging.FileHandler):
            config["filename"] = handler.baseFilename
            config["mode"] = handler.mode
            if handler.encoding is not None:
                config["encoding"] = handler.encoding
            config["delay"] = handler.delay
        return config

    def get_logger_config(logger: logging.Logger) -> JSONVal:
        return {
            "level": logger.level,
            "handlers": [handler.name for handler in logger.handlers],
            "propagate": logger.propagate,
        }

    return {
        "version": 1,
        "formatters": {hex(id(formatter)): get_formatter_config(formatter) for formatter in formatters},
        "handlers": {str(handler.name): get_handler_config(handler) for handler in handlers.values()},
        "loggers": {logger.name: get_logger_config(logger) for logger in loggers.values()},
    }
