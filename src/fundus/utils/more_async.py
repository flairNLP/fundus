import asyncio
from typing import AsyncGenerator, Iterator, Iterable, Awaitable, Optional, Any, TypeVar

_T = TypeVar("_T")

__sentinel = object()


def async_gen_interleave(*gens: AsyncGenerator[_T, None]) -> Iterator[Iterable[Awaitable[_T]]]:
    while True:
        batch = []
        for gen in gens:
            nxt = gen.__anext__()
            batch.append(nxt)
        yield batch


async def async_next(aws: Iterator[Iterable[Awaitable[_T]]], default: Optional[Any] = __sentinel) -> Iterable[_T]:
    results = []
    for coro in asyncio.as_completed(next(aws)):
        try:
            result = await coro
            results.append(result)
        except StopAsyncIteration:
            continue
    if not results:
        if default != __sentinel:
            return default
        else:
            raise StopAsyncIteration
    return iter(results)
