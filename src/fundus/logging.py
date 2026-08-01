"""Logging setup for Fundus.

Fundus follows the standard library's logger hierarchy: every module logger is a child of
the *library root* logger (``fundus``), created with :func:`create_logger` and left
unconfigured. The library root carries the log level and the handlers; children inherit
both by propagation, so a record is emitted exactly once no matter how deeply the module
is nested.

Two consequences worth knowing:

- **The level lives on the logger, not on the handler.** A logger decides which records
  reach its handlers at all; a handler level only filters further, per destination. So
  raising verbosity is :func:`set_log_level`, and a handler added via :func:`add_handler`
  never sees records the logger already dropped.
- **Propagation to the root logger stays enabled.** Fundus ships a stderr handler because
  it is an end-user tool and silent failures during a crawl would be worse than the
  convention of shipping only a ``NullHandler``. Applications that configure logging
  themselves will therefore see Fundus records twice — once from Fundus' handler and once
  from their own. They can take ownership with ``remove_handler("fundus-stderr")``, which
  leaves propagation intact so Fundus records still reach their handlers.
"""

import logging
from typing import Dict, List, Set, Union

from fundus.utils.serialization import JSONVal

__all__ = [
    "LoggerRef",
    "create_logger",
    "set_log_level",
    "add_handler",
    "remove_handler",
    "get_handlers",
    "get_current_config",
    "loggers",
]

#: Name of the library root logger. Derived from this module's package so that vendoring
#: or renaming the distribution cannot break the hierarchy invariant.
_LIBRARY_ROOT: str = __name__.split(".")[0]

_DEFAULT_LEVEL: int = logging.ERROR
_DEFAULT_HANDLER_NAME: str = "fundus-stderr"
_DEFAULT_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

#: A logger to target: its name, the logger itself, or ``None`` for the library root.
LoggerRef = Union[str, logging.Logger, None]

#: All module loggers created through :func:`create_logger`, keyed by module name.
#: They start out unconfigured — ``NOTSET`` and without handlers of their own, inheriting
#: both from the library root — and stay that way unless :func:`set_log_level` or
#: :func:`add_handler` is pointed at one of them.
loggers: Dict[str, logging.Logger] = {}


def _resolve(ref: LoggerRef) -> logging.Logger:
    """Resolve a logger reference to a Fundus logger.

    Args:
        ref: A logger name, a logger, or ``None`` for the library root logger.

    Returns:
        The referenced logger.

    Raises:
        ValueError: If the reference does not name a logger inside the Fundus hierarchy.
            Rejecting these early turns a typo — which would otherwise silently configure
            an unrelated logger and appear to do nothing — into an error at the call site.
    """
    if ref is None:
        return logging.getLogger(_LIBRARY_ROOT)

    name = ref.name if isinstance(ref, logging.Logger) else ref
    if name != _LIBRARY_ROOT and not name.startswith(f"{_LIBRARY_ROOT}."):
        raise ValueError(f"{name!r} is not a {_LIBRARY_ROOT!r} logger")
    if name.endswith(".") or ".." in name:
        raise ValueError(f"{name!r} is not a valid logger name")
    # Hand back the very logger passed in. One built directly rather than through
    # ``getLogger`` is not the registry's, and configuring its namesake there would leave
    # the caller holding an object nothing happened to.
    return ref if isinstance(ref, logging.Logger) else logging.getLogger(name)


def _configure(level: int = _DEFAULT_LEVEL) -> None:
    """Install the default setup on the library root, unless it is already configured.

    The presence of the default handler is what marks the library as configured, and the
    level is only set along with it. That makes the call a no-op once something else has
    set logging up — which a worker process depends on: ``fundus.scraping.crawler.ccnews``
    rebuilds the parent's configuration in the child, and the import of this module can
    land either side of that rebuild. Setting the level unconditionally would let a late
    import reset the worker to the default and silence everything below ``ERROR``.

    Args:
        level: The log level to set on the library root logger.
    """
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

    The returned logger is deliberately left unconfigured. It inherits its level and its
    handlers from the library root, which is what keeps a record from being emitted once
    per ancestor that happens to carry a handler.

    Args:
        name: Reference name for the logger, conventionally the module's ``__name__``.

    Returns:
        The logger for ``name``.

    Raises:
        ValueError: If ``name`` lies outside the Fundus logger hierarchy, in which case it
            would inherit neither the level nor the handlers configured here.
    """
    logger = _resolve(name)
    loggers[name] = logger
    return logger


def set_log_level(level: int, logger: LoggerRef = None) -> None:
    """Set the log level for the library, or for a single module.

    Args:
        level: The new log level.
        logger: The logger to set it on. Defaults to the library root, which applies to
            every module that has not been given a level of its own.
    """
    _resolve(logger).setLevel(level)


def add_handler(handler: logging.Handler, logger: LoggerRef = None) -> None:
    """Add a handler to the library, or to a single module.

    A handler only receives records its logger has already let through, so pair this with
    :func:`set_log_level` when the handler is meant to capture more than the current level.

    Args:
        handler: The handler to add. Must have a name set.
        logger: The logger to add it to. Defaults to the library root, which applies to
            every module. Naming a package logger — ``"fundus.scraping.pipeline"`` — covers
            that subtree.

    Raises:
        ValueError: If the handler has no name, if the target logger already carries a
            handler of that name, or if ``logger`` is outside the Fundus hierarchy.
    """
    if not handler.name:
        raise ValueError("Handlers to add must have a name set")

    target = _resolve(logger)
    if any(existing.name == handler.name for existing in target.handlers):
        raise ValueError(f"Handler with name {handler.name!r} already exists on {target.name!r}")

    target.addHandler(handler)


def remove_handler(name: str, logger: LoggerRef = None) -> logging.Handler:
    """Remove a handler from the library, or from a single module.

    The handler is returned rather than closed, so it stays usable and can be added
    elsewhere. Closing it — which a :class:`logging.FileHandler` needs to release its file
    descriptor — is left to the caller.

    Args:
        name: Name of the handler to remove.
        logger: The logger to remove it from. Defaults to the library root.

    Returns:
        The removed handler.

    Raises:
        ValueError: If the target logger carries no handler of that name, or if ``logger``
            is outside the Fundus hierarchy.
    """
    target = _resolve(logger)
    for handler in target.handlers:
        if handler.name == name:
            target.removeHandler(handler)
            return handler
    raise ValueError(f"No handler with name {name!r} on {target.name!r}")


def get_handlers(logger: LoggerRef = None) -> List[logging.Handler]:
    """Get the handlers attached to a logger.

    Only the handlers of the logger itself, not those it inherits by propagation.

    Args:
        logger: The logger to inspect. Defaults to the library root.

    Returns:
        The logger's handlers.
    """
    return list(_resolve(logger).handlers)


def get_current_config() -> Dict[str, JSONVal]:
    """Get the current logging configuration as JSON.

    Shaped for :func:`logging.config.dictConfig`, to rebuild this configuration in a worker
    process. Described are the library root and any module logger carrying a level of its
    own, so that a scoped :func:`set_log_level` survives the rebuild. Handlers only cross
    over for the library root: :func:`logging.config.dictConfig` rebuilds a handler from its
    class and a handful of arguments, which is lossy for anything richer than a stream or a
    plain file. A handler added to a *module* logger is therefore dropped in the worker,
    and one added to the library root arrives as a reconstruction, not as itself.

    Returns:
        The current logging configuration as JSON.
    """
    library_root = _resolve(None)
    handlers: Dict[str, logging.Handler] = {handler.name: handler for handler in library_root.handlers if handler.name}
    formatters: Set[logging.Formatter] = {
        handler.formatter for handler in handlers.values() if handler.formatter is not None
    }
    scoped = [logger for logger in loggers.values() if logger.level != logging.NOTSET]

    def get_formatter_config(formatter: logging.Formatter) -> JSONVal:
        return {"format": formatter._fmt}

    def get_handler_config(handler: logging.Handler) -> Dict[str, JSONVal]:
        config: Dict[str, JSONVal] = {
            "level": handler.level,
            "class": handler.__class__.__module__ + "." + handler.__class__.__name__,
        }
        if handler.formatter is not None:
            config["formatter"] = hex(id(handler.formatter))
        if isinstance(handler, logging.FileHandler):
            config["filename"] = handler.baseFilename
            config["mode"] = handler.mode
            if handler.encoding is not None:
                config["encoding"] = handler.encoding
            config["delay"] = handler.delay
        return config

    return {
        "version": 1,
        # Without this, reconfiguring a worker disables every logger it has already
        # imported that is not named below — including curl_cffi's and urllib3's.
        "disable_existing_loggers": False,
        "formatters": {hex(id(formatter)): get_formatter_config(formatter) for formatter in formatters},
        "handlers": {name: get_handler_config(handler) for name, handler in handlers.items()},
        "loggers": {
            library_root.name: {
                "level": library_root.level,
                # Drawn from the same filtered mapping: naming a handler the "handlers"
                # key above left out makes dictConfig reject the whole configuration.
                "handlers": list(handlers),
                "propagate": library_root.propagate,
            },
            **{logger.name: {"level": logger.level, "propagate": logger.propagate} for logger in scoped},
        },
    }
