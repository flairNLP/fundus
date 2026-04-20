import contextlib
import json
import threading
from typing import Callable, Dict, List, Optional, TypeVar, Union, overload

from bidict import bidict

from fundus.logging import create_logger

_T = TypeVar("_T")

logger = create_logger(__name__)

__DEFAULT_EVENTS__: List[str] = ["stop"]

_sentinel = object()


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
            event_factory: An optional callable used to create new Event objects.
                Receives the event name and returns a threading.Event. If None,
                a plain threading.Event() is used.
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
    """A thread-safe event registry for named entities running in threads.

    Each named entity (identified by a string alias) gets its own
    :class:`ThreadEventDict` holding its events.  While a thread is running,
    ``_aliases`` maps the alias to the active thread ID so that ``key=None``
    lookups inside the thread resolve correctly.  When the thread exits (via
    :meth:`context`), only the alias→thread-ID mapping is removed;
    ``_events[alias]`` persists so that other threads can still read or write
    those events after the thread has finished (e.g. the main loop checking
    whether a publisher was already told to stop).

    Both broadcast and targeted communication are supported.  Because targeted
    communication requires a stable identifier, all entities must be registered
    under a string alias via :meth:`context` or :meth:`alias` before events
    can be accessed.

    Attributes:
        _events (Dict[str, ThreadEventDict]): Mapping of alias to its events.
            Entries persist after the thread exits.
        _aliases (bidict[str, int]): Bidirectional mapping of *active* aliases
            to thread IDs.  An alias is present here only while its associated
            thread is running.
        _lock (threading.RLock): Re-entrant lock for thread safety.
    """

    def __init__(self, default_events: Optional[List[str]] = None):
        """
        Initialize a new EventDict.

        Args:
            default_events: Event names that are automatically available for
                every registered alias (e.g. ``["stop"]``).
        """

        def event_factory(name: str) -> threading.Event:
            new = threading.Event()
            if name in self._futures:
                new.set()
            return new

        self.default_events = default_events
        self._event_factory = event_factory
        self._futures: List[str] = []
        self._events: Dict[str, ThreadEventDict] = {}
        self._aliases: bidict[str, int] = bidict()
        self._lock = threading.RLock()
        self._main_context_lock = threading.Lock()

    @staticmethod
    def _get_identifier() -> int:
        """Return the current thread's unique identifier."""
        return threading.get_ident()

    def _resolve(self, key: Optional[str]) -> str:
        """Resolve ``None`` to the calling thread's alias, or return ``key`` unchanged.

        Should only be called while holding the internal lock.

        Args:
            key: An alias string, or ``None`` to use the calling thread's alias.

        Returns:
            The alias string used as the key in ``_events``.

        Raises:
            RuntimeError: If ``key`` is ``None`` and the current thread has no
                active context.
        """
        if key is None:
            ident = self._get_identifier()
            if ident in self._aliases.inv:
                return self._aliases.inv[ident]
            raise RuntimeError("Current thread has no active context. Pass an explicit alias key.")
        return key

    def _pretty_resolve(self, key: Optional[str]) -> str:
        """Resolve a key to a human-readable string for logging.

        Should only be called while holding the internal lock.

        Args:
            key: Alias string or ``None`` (current thread).

        Returns:
            A formatted string such as ``"7740   (Sportschau)"`` or
            ``"(Sportschau)"`` when the thread has already finished.

        Raises:
            RuntimeError: If ``key`` is ``None`` and the current thread has no
                active context.
        """
        alias = self._resolve(key)
        thread_id = self._aliases.get(alias)
        if thread_id is not None:
            return f"{thread_id:<6} ({alias})"
        return f"({alias})"

    def _alias(self, alias: str, key: Optional[int] = None):
        """Register an alias for a given thread identifier.

        Events are stored under the alias (canonical key).  If the alias is
        being registered for the first time, or is being re-registered after a
        previous thread finished, a fresh :class:`ThreadEventDict` is created
        so that stale state (e.g. a previously set ``"stop"`` event) is not
        inherited.

        Should only be called while holding the internal lock.

        Args:
            alias: The alias to assign.
            key: The thread identifier to associate with this alias.
                Defaults to the current thread's identifier.
        """
        ident = key if key is not None else self._get_identifier()
        logger.debug(f"Register alias {alias} -> {ident}")
        if alias not in self._aliases:
            # New or re-registration: create fresh events under the alias key.
            self._events[alias] = ThreadEventDict(self.default_events, self._event_factory)
        self._aliases[alias] = ident

    def register_event(self, event: str, key: Optional[str] = None):
        """Register a new event for an existing alias.

        The alias must already be registered via :meth:`context` or
        :meth:`alias` before calling this method.

        Args:
            event: The name of the event to register.
            key: Alias or ``None`` (defaults to the current thread's alias).

        Raises:
            RuntimeError: If ``key`` is ``None`` and the current thread has no
                active context.
            KeyError: If ``key`` names an alias that has never been registered.
        """
        with self._lock:
            if event not in self._events[(resolved := self._resolve(key))]:
                self._events[resolved][event] = self._event_factory(event)
                logger.debug(f"Registered event {event!r} for {self._pretty_resolve(key)}")

    def set_event(self, event: str, key: Optional[str] = None):
        """Set (trigger) an event for the specified alias.

        Args:
            event: The name of the event to set.
            key: Alias or ``None`` (defaults to the current thread's alias).
        """
        with self._lock:
            self._events[self._resolve(key)][event].set()
            logger.debug(f"Set event {event!r} for {self._pretty_resolve(key)}")

    def clear_event(self, event: str, key: Optional[str] = None):
        """Clear (reset) an event for the specified alias.

        Args:
            event: The name of the event to clear.
            key: Alias or ``None`` (defaults to the current thread's alias).
        """
        with self._lock:
            self._events[self._resolve(key)][event].clear()
            logger.debug(f"Cleared event {event!r} for {self._pretty_resolve(key)}")

    def set_for_all(self, event: Optional[str] = None, future: bool = False, active_only: bool = False):
        """Set an event for all registered aliases.

        If ``event`` is ``None``, every event for every registered alias is set.

        Args:
            event: The event name to set. If ``None``, all events are set.
            future: If ``True``, newly registered aliases will also have this
                event pre-set (via the event factory).
            active_only: If ``True``, only aliases whose threads are currently
                running are targeted; aliases whose threads have already finished
                are skipped.
        """
        with self._lock:
            if event is None:
                for key, events in self._events.items():
                    if active_only and key not in self._aliases:
                        continue
                    for name in events:
                        self.set_event(name, key)
            else:
                if future:
                    self._futures.append(event)

                for key in self._events:
                    if active_only and key not in self._aliases:
                        continue
                    self.set_event(event, key)

    def clear_for_all(self, event: Optional[str] = None):
        """Clear an event for all registered aliases.

        If the event was previously marked for future threads via
        :meth:`set_for_all` with ``future=True``, that mark is also removed.

        If ``event`` is ``None``, every event for every registered alias is
        cleared.

        Args:
            event: The event name to clear. If ``None``, all events are cleared.
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

    def is_event_set(self, event: str, key: Optional[str] = None) -> bool:
        """Check whether a specific event is set for the given alias.

        Args:
            event: The name of the event to check.
            key: Alias or ``None`` (defaults to the current thread's alias).

        Returns:
            ``True`` if the event is set, ``False`` otherwise.

        Raises:
            RuntimeError: If ``key`` is ``None`` and the current thread has no
                active context.
            KeyError: If ``key`` names an alias that has never been registered.
        """
        with self._lock:
            return self._events[self._resolve(key)][event].is_set()

    @contextlib.contextmanager
    def context(self, alias: str, key: Optional[int] = None):
        """Context manager that registers an alias for the duration of a block.

        On entry the alias is bound to the current (or given) thread ID so that
        ``key=None`` lookups inside the thread resolve correctly.  On exit only
        the alias→thread-ID mapping is removed; ``_events[alias]`` is kept
        alive so that other threads can still read those events after this
        thread finishes.  Stale state is cleared on the next :meth:`reset` or
        when the alias is re-registered via a new ``context()`` call.

        Args:
            alias: The alias name to register.
            key: Thread identifier to associate with the alias. Defaults to the
                current thread's identifier.
        """
        try:
            with self._lock:
                self._alias(alias, key)
            yield
        finally:
            with self._lock:
                self._aliases.pop(alias, None)

    @contextlib.contextmanager
    def main_context(self, alias: str):
        """Context manager for the main thread; resets all state on exit.

        Only one main context may be active at a time.

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
        """Register an alias for a thread without using a context manager.

        Prefer :meth:`context` for automatic cleanup on thread exit.  Use this
        method only when the alias lifetime cannot be expressed as a ``with``
        block (e.g. a long-lived background thread).

        Args:
            alias: The alias name to register.
            key: Thread identifier to associate with the alias. Defaults to the
                current thread's identifier.
        """
        with self._lock:
            self._alias(alias, key)

    @overload
    def get_alias(self, ident: int) -> str:
        ...

    @overload
    def get_alias(self, ident: int, default: _T) -> Union[str, _T]:
        ...

    def get_alias(self, ident: int, default=_sentinel):
        """Return the alias associated with a thread identifier.

        Args:
            ident: The thread identifier.
            default: Value to return if no alias is found. If omitted, raises
                ``KeyError``.

        Returns:
            The alias string, or ``default`` if the thread has no alias.
        """
        if default is _sentinel:
            return self._aliases.inv[ident]
        return self._aliases.inv.get(ident, default)

    def get(self, event: str, key: Optional[str] = None) -> threading.Event:
        """Return the raw :class:`threading.Event` for the given alias and event name.

        Args:
            event: The name of the event to retrieve.
            key: Alias or ``None`` (defaults to the current thread's alias).

        Returns:
            The :class:`threading.Event` object.
        """
        with self._lock:
            return self._events[self._resolve(key)][event]

    def reset(self):
        """Clear all events, aliases, and futures.

        Called automatically by :meth:`main_context` on exit.
        """
        with self._lock:
            self._futures = []
            self._events = {}
            self._aliases = bidict()

    def __str__(self):
        def _entry(alias: str) -> str:
            thread_id = self._aliases.get(alias, "finished")
            header = f"{alias} --> {thread_id}"
            serialized = json.dumps(self._events[alias], indent=2, ensure_ascii=False, default=lambda o: o.is_set())
            return f"{header}:\n{serialized}"

        entries = [_entry(alias) for alias in self._events]
        return "\n".join(entries) if entries else "Empty Event Dictionary"


__EVENTS__: EventDict = EventDict(default_events=__DEFAULT_EVENTS__)
