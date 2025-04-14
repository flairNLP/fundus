import threading
from collections import defaultdict
from typing import Any, Dict, Optional, Union

from fundus.logging import create_logger

logger = create_logger(__name__)


class EventDict:
    """A thread-safe event dictionary.

    Events are registered by name and stored per thread in a dictionary, using the
    thread's identifier as the key. For example, calling `register_event("stop")`
    registers a "stop" event for the current thread's identifier.

    To enhance usability, threads can be assigned aliases. Calling
    `register_event("stop", "BR")` registers the "stop" event (if it is not already
    registered) for the current thread and automatically creates an alias mapping
    "BR" to the thread's identifier.
    """

    def __init__(self):
        self._events: Dict[int, Dict[str, threading.Event]] = defaultdict(dict)
        self._aliases: Dict[Any, int] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _get_identifier() -> int:
        return threading.get_ident()

    def _resolve(self, key: Union[int, str, None]) -> int:
        """Resolves a given key to a thread identifier

        Should only be used within a Lock!

        Args:
            key: Key to resolve

        Returns:
            Resolved thread identifier
        """
        if key is None:
            return self._get_identifier()
        if isinstance(key, int):
            return key
        return self._aliases[key]

    def _alias(self, alias: str, key: Optional[int] = None):
        self._aliases[alias] = key if key else self._get_identifier()
        logger.debug(f"Registered alias {alias} -> {self._aliases[alias]}")

    def register_event(self, event: str, key: Union[int, str, None] = None):
        with self._lock:
            if isinstance(key, str) and key not in self._aliases:
                self._alias(key)
            if (resolved := self._resolve(key)) not in self._events:
                self._events[resolved][event] = threading.Event()
                logger.debug(f"Registered event {event!r} for {resolved}")

    def set_event(self, event: str, key: Union[int, str, None] = None):
        with self._lock:
            self._events[self._resolve(key)][event].set()
            logger.debug(f"Set event {event!r} for {self._resolve(key)}")

    def clear_event(self, event: str, key: Union[int, str, None] = None):
        with self._lock:
            self._events[self._resolve(key)][event].clear()
            logger.debug(f"Cleared event {event!r} for {self._resolve(key)}")

    def set_for_all(self, event: Optional[str] = None):
        """Set <event> for all registered keys

        If <event> is None, all events for every registered key will be set.
        Args:
            event: The event to set. Defaults to None.

        Returns:
            None
        """
        with self._lock:
            for events in self._events.values():
                if event is not None and event in events:
                    events[event].set()
                else:
                    for flag in events.values():
                        flag.set()

    def clear_for_all(self, event: Optional[str] = None):
        """Clear <event> for all registered keys

        If <event> is None, all events for every registered key will be cleared.
        Args:
            event: The event to clear. Defaults to None.

        Returns:
            None
        """
        with self._lock:
            for events in self._events.values():
                if event is not None and event in events:
                    events[event].clear()
                else:
                    for flag in events.values():
                        flag.clear()

    def is_event_set(self, event: str, key: Union[int, str, None] = None) -> bool:
        with self._lock:
            return self._events[self._resolve(key)][event].is_set()

    def alias(self, alias: str, key: Optional[int] = None):
        with self._lock:
            self._alias(alias, key)

    def remove_alias(self, alias: str):
        with self._lock:
            self._aliases.pop(alias, None)

    def get(self, event: str, key: Optional[Union[int, str, None]] = None) -> threading.Event:
        with self._lock:
            return self._events[self._resolve(key)][event]


__EVENTS__: EventDict = EventDict()
