import contextlib
import multiprocessing
from functools import lru_cache
from multiprocessing.managers import BaseManager
from threading import current_thread
from typing import Callable, Generic, Iterator, Optional, Tuple, TypeVar, cast

import dill
from tqdm import tqdm
from typing_extensions import ParamSpec

_T = TypeVar("_T")
_P = ParamSpec("_P")


def get_execution_context() -> Tuple[str, Optional[int]]:
    """Return the name and identifier of the current execution context.

    If running inside a non-main process, returns that process's name and PID; otherwise
    returns the current thread's name and thread id.

    Returns:
        Tuple[str, Optional[int]]: The context's name and its integer identifier.
    """
    if multiprocessing.current_process().name != "MainProcess":
        process = multiprocessing.current_process()
        return process.name, process.ident
    else:
        thread = current_thread()
        return thread.name, thread.ident


class TQDMManager(BaseManager):
    """multiprocessing manager exposing a shared tqdm proxy so worker processes drive one progress bar."""

    def __init__(self, *args, **kwargs):
        """Initialize the manager and register tqdm so it can be created behind a proxy."""
        super().__init__(*args, **kwargs)
        self.register("_tqdm", tqdm)

    def tqdm(self, *args, **kwargs) -> tqdm:
        """Create and return a manager-hosted (proxied) tqdm instance from the given tqdm args."""
        return getattr(self, "_tqdm")(*args, **kwargs)


@contextlib.contextmanager
def get_proxy_tqdm(*args, **kwargs) -> Iterator[tqdm]:
    """Yield a manager-backed tqdm proxy that can be shared across processes.

    Init args are forwarded verbatim and are the same as for any other tqdm instance. The
    backing manager is started on entry and shut down on exit.

    Args:
        *args: Positional tqdm arguments.
        **kwargs: Keyword tqdm arguments.

    Yields:
        tqdm: A self-managed, proxied tqdm instance.
    """
    manager = TQDMManager()
    try:
        manager.start()
        yield manager.tqdm(*args, **kwargs)
    finally:
        manager.shutdown()


class dill_wrapper(Generic[_P, _T]):
    """Callable wrapper that dill-serializes its target so it survives multiprocessing pickling."""

    def __init__(self, target: Callable[_P, _T]):
        """Wraps function in dill serialization.

        This is in order to use unpickable functions within multiprocessing.

        Args:
            target: The function to wrap.
        """
        self._serialized_target: bytes = dill.dumps(target)

    @lru_cache
    def _deserialize(self) -> Callable[_P, _T]:
        """Deserialize and cache the wrapped target on first use (once per process)."""
        return cast(Callable[_P, _T], dill.loads(self._serialized_target))

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        """Deserialize the target (cached) and invoke it with the given arguments."""
        return self._deserialize()(*args, **kwargs)
