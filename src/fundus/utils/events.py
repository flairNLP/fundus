import json
import threading
from collections import defaultdict
from typing import Dict, List, Optional, Union

from bidict import bidict

from fundus.logging import create_logger

logger = create_logger(__name__)

__DEFAULT_EVENTS__: List[str] = ["stop"]


class ThreadEventDict(Dict[str, threading.Event]):
    """A dictionary that creates threading.Event() objects on demand for certain keys.

    This class behaves like a standard dictionary but automatically creates
    `threading.Event` objects when specific keys (provided via `default_events`)
    are accessed. This is similar to `defaultdict`, but the auto-creation only
    applies to those specific keys.

    Attributes:
        _default_events (List[str]): List of event names for which Events will be auto-created.
    """

    def __init__(self, default_events: Optional[List[str]] = None):
        """
        Initialize a new ThreadEventDict.

        Args:
            default_events: A list of event names for which Event objects
                should be automatically created when accessed.
        """
        super().__init__()
        self._default_events = default_events or []

    def __getitem__(self, item: str) -> threading.Event:
        """
        Get the Event associated with the given item.

        If the key does not exist and is in `_default_events`, a new
        `threading.Event` is created, stored, and returned.

        Args:
            item: The event name to retrieve.

        Returns:
            threading.Event: The event associated with the key.

        Raises:
            KeyError: If the key is not present and not in `_default_events`.
        """
        try:
            return super().__getitem__(item)
        except KeyError as e:
            if item in self._default_events:
                event = threading.Event()
                self[item] = event
                return event
            raise e


class EventDict:
    """A thread-safe event registry for managing thread-local events with optional aliases.

    This class maintains per-thread event dictionaries, allowing threads to
    register, set, and clear named `threading.Event` objects in an isolated
    and synchronized manner.

    Aliases can be assigned to thread identifiers for convenience. Each alias
    maps uniquely to a thread ID, allowing event access via human-readable names.

    Attributes:
        _events (Dict[int, ThreadEventDict]): Mapping of thread IDs to their events.
        _aliases (bidict[str, int]): Bidirectional mapping of aliases to thread IDs.
        _lock (threading.RLock): A re-entrant lock to ensure thread safety.
    """

    def __init__(self, default_events: Optional[List[str]] = None):
        """
        Initialize a new EventDict.

        Args:
            default_events: A list of event names that are automatically available
                for all threads (e.g., ["stop"]).
        """
        self.default_events = default_events
        self._events: Dict[int, ThreadEventDict] = defaultdict(lambda: ThreadEventDict(self.default_events))
        self._aliases: bidict[str, int] = bidict()
        self._lock = threading.RLock()

    @staticmethod
    def _get_identifier() -> int:
        """
        Get the current thread's unique identifier.

        Returns:
            int: The current thread's identifier.
        """
        return threading.get_ident()

    def _resolve(self, key: Union[int, str, None]) -> int:
        """Resolve a key (thread ID, alias, or None) to a thread identifier.

        Should only be called while holding the internal lock.

        Args:
            key: The key to resolve. May be a thread ID, alias, or None.

        Returns:
            int: The resolved thread identifier.
        """
        if key is None:
            return self._get_identifier()
        if isinstance(key, int):
            return key
        return self._aliases[key]

    def _pretty_resolve(self, key: Union[int, str, None]) -> str:
        """
        Resolve a key to a human-readable identifier string, including alias if available.

        Should only be called while holding the internal lock.

        Args:
            key: Thread ID, alias, or None.

        Returns:
            str: A formatted string of the form "<thread_id> (alias)".
        """
        resolved = self._resolve(key)
        alias = f" ({self._aliases.inv[resolved]})" if resolved in self._aliases.values() else ""
        return f"{resolved:<6}{alias}"

    def _alias(self, alias: str, key: Optional[int] = None):
        """
        Register an alias for a given thread identifier.

        Should only be called while holding the internal lock.

        Args:
            alias: The alias to assign.
            key: The thread identifier to associate with this alias.
                If None, the current thread's identifier is used.
        """
        self._aliases[alias] = key if key else self._get_identifier()
        if (ident := self._resolve(alias)) not in self._events:
            # noinspection PyStatementEffect
            # Since defaultdict doesn't provide a direct way to create defaults,
            # we simulate it by accessing the key.
            self._events[ident]
        logger.debug(f"Registered alias {alias} -> {self._aliases[alias]}")

    def register_event(self, event: str, key: Union[int, str, None] = None):
        """
        Register a new event for the specified thread or alias.

        If the alias does not exist, it is automatically created.

        Args:
            event: The name of the event to register.
            key: Thread ID, alias, or None (defaults to the current thread).
        """
        with self._lock:
            if isinstance(key, str) and key not in self._aliases:
                self._alias(key)
            if event not in self._events[(resolved := self._resolve(key))]:
                self._events[resolved][event] = threading.Event()
                logger.debug(f"Registered event {event!r} for {self._pretty_resolve(key)}")

    def set_event(self, event: str, key: Union[int, str, None] = None):
        """
        Set (trigger) an event for the specified thread.

        Args:
            event: The name of the event to set.
            key: Thread ID, alias, or None (defaults to the current thread).
        """
        with self._lock:
            self._events[self._resolve(key)][event].set()
            logger.debug(f"Set event {event!r} for {self._pretty_resolve(key)}")

    def clear_event(self, event: str, key: Union[int, str, None] = None):
        """
        Clear (reset) an event for the specified thread.

        Args:
            event: The name of the event to clear.
            key: Thread ID, alias, or None (defaults to the current thread).
        """
        with self._lock:
            self._events[self._resolve(key)][event].clear()
            logger.debug(f"Cleared event {event!r} for {self._pretty_resolve(key)}")

    def set_for_all(self, event: Optional[str] = None):
        """Set an event for all registered threads.

        If `event` is None, all events for every registered thread are set.

        Args:
            event: The event name to set. If None, all events are set.
        """
        with self._lock:
            if event is None:
                for ident, events in self._events.items():
                    for name in events:
                        self.set_event(name, ident)
            else:
                for ident in self._events:
                    self.set_event(event, ident)

    def clear_for_all(self, event: Optional[str] = None):
        """Clear an event for all registered threads.

        If `event` is None, all events for every registered thread are cleared.

        Args:
            event: The event name to clear. If None, all events are cleared.
        """
        with self._lock:
            if event is None:
                for ident, events in self._events.items():
                    for name in events:
                        self.clear_event(name, ident)
            else:
                for ident in self._events:
                    self.clear_event(event, ident)

    def is_event_set(self, event: str, key: Union[int, str, None] = None) -> bool:
        """
        Check if a specific event is set for a given thread.

        Args:
            event: The name of the event to check.
            key: Thread ID, alias, or None (defaults to the current thread).

        Returns:
            bool: True if the event is set, False otherwise.
        """
        with self._lock:
            return self._events[self._resolve(key)][event].is_set()

    def alias(self, alias: str, key: Optional[int] = None):
        """
        Public wrapper to register an alias for a thread.

        Args:
            alias: The alias name to register.
            key: Optional thread identifier to associate with the alias.
                Defaults to the current thread if not provided.
        """
        with self._lock:
            self._alias(alias, key)

    def get_alias(self, ident: int) -> str:
        """
        Get the alias associated with a thread identifier.

        Args:
            ident: The thread identifier.

        Returns:
            str: The alias associated with the identifier.
        """
        return self._aliases.inv[ident]

    def remove_alias(self, alias: str):
        """
        Remove an alias from the alias mapping.

        Args:
            alias: The alias to remove.
        """
        with self._lock:
            self._aliases.pop(alias, None)

    def get(self, event: str, key: Optional[Union[int, str, None]] = None) -> threading.Event:
        """
        Get the event object associated with the given event name and thread.

        Args:
            event: The name of the event to retrieve.
            key: Thread ID, alias, or None (defaults to the current thread).

        Returns:
            threading.Event: The event object.
        """
        with self._lock:
            return self._events[self._resolve(key)][event]

    def reset(self):
        with self._lock:
            self._events = defaultdict(lambda: ThreadEventDict(self.default_events))
            self._aliases = bidict()

    def __str__(self):
        def _entry(thread: int) -> str:
            alias = self._aliases.inv.get(thread, None)
            serialized = json.dumps(self._events[thread], indent=2, ensure_ascii=False, default=lambda o: o.set())
            return f"{alias if alias else 'None'} --> {thread}: \n" + serialized

        events = [_entry(ident) for ident in self._events]
        return "\n".join(events) if events else "Empty Event Dictionary"


__EVENTS__: EventDict = EventDict(default_events=__DEFAULT_EVENTS__)
