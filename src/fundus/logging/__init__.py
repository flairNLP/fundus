"""Logging setup for Fundus.

Every module logger is a child of the library root logger (``fundus``), which carries the
log level and the handlers; children are created unconfigured and inherit both. Two things
follow that are worth knowing:

- **The level lives on the logger, not the handler.** A handler only filters further, per
  destination, so a handler added via :func:`add_handler` never sees records
  :func:`set_log_level` already dropped.
- **Propagation to the root logger stays on.** Fundus ships a stderr handler, unusually for
  a library, because silent failures during a crawl would be worse. An application that
  configures logging itself will therefore see records twice, and can take ownership with
  ``remove_handler("fundus-stderr")`` without losing them.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Union

__all__ = [
    "LoggerRef",
    "create_logger",
    "set_log_level",
    "add_handler",
    "remove_handler",
    "get_handlers",
    "loggers",
]

# Derived from this module's package so vendoring or renaming cannot break the hierarchy.
_LIBRARY_ROOT: str = __name__.split(".")[0]

_DEFAULT_LEVEL: int = logging.ERROR
_DEFAULT_HANDLER_NAME: str = "fundus-stderr"
_DEFAULT_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

#: A logger to target: its name, the logger itself, or ``None`` for the library root.
LoggerRef = Union[str, logging.Logger, None]

#: Module loggers created through :func:`create_logger`, keyed by module name. They are
#: ``NOTSET`` and hold no handlers unless :func:`set_log_level` or :func:`add_handler` is
#: pointed at one of them.
loggers: Dict[str, logging.Logger] = {}


def _resolve(ref: LoggerRef) -> logging.Logger:
    """Resolve a name, a logger, or ``None`` to a Fundus logger, rejecting anything else."""
    if ref is None:
        return logging.getLogger(_LIBRARY_ROOT)

    name = ref.name if isinstance(ref, logging.Logger) else ref
    if name != _LIBRARY_ROOT and not name.startswith(f"{_LIBRARY_ROOT}."):
        raise ValueError(f"{name!r} is not a {_LIBRARY_ROOT!r} logger")
    if name.endswith(".") or ".." in name:
        raise ValueError(f"{name!r} is not a valid logger name")
    # Hand back the logger passed in: one built directly is not the registry's, and
    # configuring its namesake would leave the caller holding an untouched object.
    return ref if isinstance(ref, logging.Logger) else logging.getLogger(name)


def _configure(level: int = _DEFAULT_LEVEL) -> None:
    """Install the default handler and level, unless something already configured them."""
    library_root = _resolve(None)
    if any(handler.name == _DEFAULT_HANDLER_NAME for handler in library_root.handlers):
        return

    library_root.setLevel(level)

    # Left at NOTSET on purpose: the logger is the gate, the handler emits what reaches it.
    handler = logging.StreamHandler()
    handler.set_name(_DEFAULT_HANDLER_NAME)
    handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
    library_root.addHandler(handler)


_configure()


def create_logger(name: str) -> logging.Logger:
    """Create the logger for a Fundus module.

    The logger is left unconfigured and inherits its level and handlers from the library
    root, which is what keeps a record from being emitted once per ancestor holding a handler.

    Args:
        name: Reference name for the logger, conventionally the module's ``__name__``.

    Returns:
        The logger for ``name``.

    Raises:
        ValueError: If ``name`` lies outside the Fundus logger hierarchy, where it would
            inherit neither the level nor the handlers configured here.
    """
    logger = _resolve(name)
    loggers[name] = logger
    return logger


def set_log_level(level: int, logger: LoggerRef = None) -> None:
    """Set the log level for the library, or for a single module.

    Args:
        level: The new log level.
        logger: The logger to set it on. Defaults to the library root, which applies to every
            module that has not been given a level of its own.
    """
    _resolve(logger).setLevel(level)


def add_handler(handler: logging.Handler, logger: LoggerRef = None) -> None:
    """Add a handler to the library, or to a single module.

    A handler only receives records its logger let through, so pair this with
    :func:`set_log_level` when it is meant to capture more than the current level.

    Args:
        handler: The handler to add. Must have a name set.
        logger: The logger to add it to. Defaults to the library root, which applies to every
            module. Naming a package logger — ``"fundus.scraping.pipeline"`` — covers that
            subtree.

    Raises:
        ValueError: If the handler has no name, if the target logger already carries a handler
            of that name, or if ``logger`` is outside the Fundus hierarchy.
    """
    if not handler.name:
        raise ValueError("Handlers to add must have a name set")

    target = _resolve(logger)
    if any(existing.name == handler.name for existing in target.handlers):
        raise ValueError(f"Handler with name {handler.name!r} already exists on {target.name!r}")

    target.addHandler(handler)


def remove_handler(name: str, logger: LoggerRef = None) -> logging.Handler:
    """Remove a handler from the library, or from a single module.

    The handler is returned rather than closed, so it stays usable elsewhere. Closing it —
    which a :class:`logging.FileHandler` needs to release its descriptor — is the caller's.

    Args:
        name: Name of the handler to remove.
        logger: The logger to remove it from. Defaults to the library root.

    Returns:
        The removed handler.

    Raises:
        ValueError: If the target logger carries no handler of that name, or if ``logger`` is
            outside the Fundus hierarchy.
    """
    target = _resolve(logger)
    for handler in target.handlers:
        if handler.name == name:
            target.removeHandler(handler)
            return handler
    raise ValueError(f"No handler with name {name!r} on {target.name!r}")


def get_handlers(logger: LoggerRef = None) -> List[logging.Handler]:
    """Get a logger's own handlers, not those it inherits by propagation.

    Args:
        logger: The logger to inspect. Defaults to the library root.

    Returns:
        The logger's handlers.
    """
    return list(_resolve(logger).handlers)
