from dataclasses import dataclass
from functools import wraps
from typing import Type, Callable, Any, Tuple, Dict


@dataclass
class Result:
    func: Callable[[Any], Any]
    args: Tuple[Any, ...]
    kwargs: Dict[str, Any]


@dataclass
class Succeeded(Result):
    result: Any


@dataclass
class Failed(Result):
    exception: Exception


def error_stated(*exceptions: Type[Exception]):
    if not exceptions:
        raise ValueError("function <error_stated> requires one or more exception types as parameter")

    def decorator(func: Callable[[Any], Any]):

        @wraps(func)
        def wrapper(*args, **kwargs) -> Result:
            try:
                result = func(*args, **kwargs)
                return Succeeded(func, args, kwargs, result)
            except exceptions as exc:
                return Failed(func, args, kwargs, exc)

        return wrapper

    return decorator
