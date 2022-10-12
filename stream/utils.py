from collections.abc import Collection
from itertools import islice, cycle
from typing import Callable, Iterable, Mapping


def listify(obj: ...) -> list:
    if isinstance(obj, Mapping):
        return [obj]
    elif isinstance(obj, Collection):
        return list(obj)
    else:
        return [obj]


def each(fn: Callable, it: Iterable):
    for x in it:
        fn(x)


def nth_cycle(it: Iterable, n: int = None):
    return islice(cycle(it), n) if n else cycle(it)
