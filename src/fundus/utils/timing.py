import random
import time
from functools import wraps
from typing import Callable, Tuple, TypeVar

from typing_extensions import ParamSpec

_T = TypeVar("_T")
_P = ParamSpec("_P")


def random_sleep(func: Callable[_P, _T], between: Tuple[float, float]) -> Callable[_P, _T]:
    """Wrap func so each invocation first sleeps a random duration within the (low, high) interval (seconds)."""

    @wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        time.sleep(random.uniform(*between))
        return func(*args, **kwargs)

    return wrapper
