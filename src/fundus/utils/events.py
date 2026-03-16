import contextlib
import json
import threading
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Union

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

    def __init__(
        self,
        default_events: Optional[List[str]] = None,
        event_factory: Optional[Callable[[str], threading.Event]] = None,
    ):
        """
        Initialize a new ThreadEventDict.

        Args:
            default_events: A list of event names for which Event objects
                should be automatically created when accessed.
        """
        super().__init__()
        self._default_events = default_events or []
        self._event_factory = event_factory

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
                event = threading.Event() if not self._event_factory else self._event_factory(item)
                self[item] = event
                return event
            raise e


class EventDict:
    """A thread-safe event registry for managing named-entity events with optional thread association.

    Events are stored primarily by alias (canonical, persistent key). While a thread is running,
    ``_aliases`` maps the alias to the active thread ID so that ``key=None`` lookups inside
    the thread resolve to the correct event dict.  When the thread exits (via :meth:`context`),
    only the alias→thread-ID mapping is removed; ``_events[alias]`` persists so that other
    threads can still read/write those events after the thread has finished.

    Attributes:
        _events (Dict[Union[int, str], ThreadEventDict]): Mapping of canonical keys to their
            events.  Named entities use their alias (str) as the key; anonymous threads use
            their thread ID (int).
        _aliases (bidict[str, int]): Bidirectional mapping of *active* aliases to thread IDs.
            An alias is present here only while its associated thread is running.
        _lock (threading.RLock): A re-entrant lock to ensure thread safety.
    """

    def __init__(self, default_events: Optional[List[str]] = None):
        """
        Initialize a new EventDict.

        Args:
            default_events: A list of event names that are automatically available
                for all threads (e.g., ["stop"]).
        """

        def event_factory(name: str) -> threading.Event:
            new = threading.Event()
            if name in self._futures:
                new.set()
            return new

        self.default_events = default_events
        self._event_factory = event_factory
        self._futures: List[str] = []
        self._events: Dict[Union[int, str], ThreadEventDict] = defaultdict(
            lambda: ThreadEventDict(self.default_events, self._event_factory)
        )
        self._aliases: bidict[str, int] = bidict()
        self._lock = threading.RLock()
        self._main_context_lock = threading.Lock()
        self._global_events: Dict[str, threading.Event] = {
            "shutdown": threading.Event(),
        }

    @staticmethod
    def _get_identifier() -> int:
        """
        Get the current thread's unique identifier.

        Returns:
            int: The current thread's identifier.
        """
        return threading.get_ident()

    def _resolve(self, key: Union[int, str, None]) -> Union[int, str]:
        """Resolve a key (thread ID, alias, or None) to the canonical event-dict key.

        The canonical key is the alias string for named entities (even after the thread
        has exited) and the integer thread ID for anonymous threads.

        Should only be called while holding the internal lock.

        Args:
            key: The key to resolve. May be a thread ID, alias, or None.

        Returns:
            Union[int, str]: The canonical key for ``_events``.

        Raises:
            KeyError: If a string alias is not registered and has no persisted events.
        """
        if key is None:
            ident = self._get_identifier()
            # Named thread: resolve to alias (canonical key)
            if ident in self._aliases.inv:
                return self._aliases.inv[ident]
            return ident
        if isinstance(key, int):
            if key in self._aliases.inv:
                return self._aliases.inv[key]
            return key
        # String (alias) key
        if key in self._aliases:
            return key  # Active alias – canonical key
        if key in self._events:
            return key  # Thread has finished but events persist under alias key
        raise KeyError(key)

    def _pretty_resolve(self, key: Union[int, str, None]) -> str:
        """
        Resolve a key to a human-readable identifier string, including alias if available.

        Should only be called while holding the internal lock.

        Args:
            key: Thread ID, alias, or None.

        Returns:
            str: A formatted string such as ``"7740   (Sportschau)"`` or ``"(Sportschau)"``.
        """
        resolved = self._resolve(key)
        if isinstance(resolved, str):
            # Named entity – show thread ID if the thread is still active
            thread_id = self._aliases.get(resolved)
            if thread_id is not None:
                return f"{thread_id:<6} ({resolved})"
            return f"({resolved})"
        else:
            alias = self._aliases.inv.get(resolved)
            return f"{resolved:<6}{f' ({alias})' if alias else ''}"

    def _alias(self, alias: str, key: Optional[int] = None):
        """
        Register an alias for a given thread identifier.

        Events are stored under the alias (canonical key).  If the alias is being
        registered for the first time, or is being re-registered after a previous
        thread finished, a fresh :class:`ThreadEventDict` is created so that stale
        state (e.g. a previously set ``"stop"`` event) is not inherited.

        Should only be called while holding the internal lock.

        Args:
            alias: The alias to assign.
            key: The thread identifier to associate with this alias.
                If None, the current thread's identifier is used.
        """
        ident = key or self._get_identifier()
        logger.debug(f"Register alias {alias} -> {ident}")
        if alias not in self._aliases:
            # New or re-registration: create fresh events under the alias key
            self._events[alias] = ThreadEventDict(self.default_events, self._event_factory)
        self._aliases[alias] = ident
        # _events[ident] is NOT created here – the canonical key is the alias string,
        # and _resolve(None) inside the thread will return the alias via _aliases.inv.

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
                self._events[resolved][event] = self._event_factory(event)
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

    def set_for_all(self, event: Optional[str] = None, future: bool = False):
        """Set an event for all registered threads.

        If `event` is None, all events for every registered thread are set.

        Args:
            event: The event name to set. If None, all events are set.
            future: If True, the event will be set for all future threads as well.
        """
        with self._lock:
            if event is None:
                for key, events in self._events.items():
                    for name in events:
                        self.set_event(name, key)
            else:
                if future:
                    self._futures.append(event)

                for key in self._events:
                    self.set_event(event, key)

    def clear_for_all(self, event: Optional[str] = None):
        """Clear an event for all registered threads.

        If the event was previously set with set_for_all(..., future=True),
        the event won't be set for future events anymore.

        If `event` is None, all events for every registered thread are cleared.

        Args:
            event: The event name to clear. If None, all events are cleared.
        """
        with self._lock:
            if event is None:
                for key, events in self._events.items():
                    for name in events:
                        self.clear_event(name, key)
            else:
                if event in self._futures:
                    self._futures.remove(event)

                for key in self._events:
                    self.clear_event(event, key)

    def is_event_set(self, event: str, key: Union[int, str, None] = None) -> bool:
        """
        Check if a specific event is set for a given thread.

        Args:
            event: The name of the event to check.
            key: Thread ID, alias, or None (defaults to the current thread).

        Returns:
            bool: True if the event is set, False otherwise.

        Raises:
            KeyError: If ``key`` is a string alias that was never registered.
        """
        with self._lock:
            return self._events[self._resolve(key)][event].is_set()

    @contextlib.contextmanager
    def context(self, alias: str, key: Optional[int] = None):
        """
        Context manager that registers an alias for the duration of a block.

        On entry, the alias is bound to the current (or given) thread ID so that
        ``key=None`` lookups inside the thread resolve correctly.  On exit, only
        the alias→thread-ID mapping is removed; ``_events[alias]`` is kept alive
        so that other threads can still access those events after this thread
        finishes.  Events are cleaned up on the next :meth:`reset` call or when
        the alias is re-registered via a new ``context()`` invocation.

        Args:
            alias: The alias name to register.
            key: Optional thread identifier to associate with the alias.
                Defaults to the current thread if not provided.
        """
        try:
            with self._lock:
                self._alias(alias, key)
            yield
        finally:
            with self._lock:
                # Remove the active alias→thread mapping so the thread ID can be
                # reused by other threads without interference.  The alias-keyed
                # events in _events[alias] are intentionally kept so that other
                # threads (e.g. the main crawl loop) can still read them.
                self._aliases.pop(alias, None)

    @contextlib.contextmanager
    def main_context(self, alias: str):
        """Context manager that registers an alias for the main thread and resets all state on exit.

        Only one main context may be active at a time. Attempting to enter a second one raises
        ``RuntimeError``.

        Args:
            alias: The alias to register for the calling thread.

        Raises:
            RuntimeError: If a main context is already active.
        """
        if not self._main_context_lock.acquire(blocking=False):
            raise RuntimeError("A main context is already active")
        try:
            with self.context(alias):
                yield
        finally:
            self.reset()
            self._main_context_lock.release()

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
            self._futures = []
            self._events = defaultdict(lambda: ThreadEventDict(self.default_events, self._event_factory))
            self._aliases = bidict()

    def __str__(self):
        def _entry(key: Union[int, str]) -> str:
            if isinstance(key, str):
                alias = key
                thread_id = self._aliases.get(key, "finished")
                header = f"{alias} --> {thread_id}"
            else:
                alias = self._aliases.inv.get(key, "None")
                header = f"{alias} --> {key}"
            serialized = json.dumps(self._events[key], indent=2, ensure_ascii=False, default=lambda o: o.set())
            return f"{header}: \n" + serialized

        events = [_entry(key) for key in self._events]
        return "\n".join(events) if events else "Empty Event Dictionary"


__EVENTS__: EventDict = EventDict(default_events=__DEFAULT_EVENTS__)
