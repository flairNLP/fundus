import asyncio
from typing import AsyncIterator, Iterable, TypeVar, Union, overload

_T = TypeVar("_T")
_VT = TypeVar("_VT")


class _Sentinel:
    pass


__sentinel = _Sentinel()


@overload
async def async_next(iterator: AsyncIterator[_T]) -> _T:
    ...


@overload
async def async_next(iterator: AsyncIterator[_T], default: Union[_VT, _Sentinel]) -> Union[_T, _VT]:
    ...


async def async_next(iterator: AsyncIterator[_T], default: Union[_VT, _Sentinel] = __sentinel) -> Union[_T, _VT]:
    task = iterator.__anext__()
    try:
        return await task
    except StopAsyncIteration:
        if not isinstance(default, _Sentinel):
            return default
        else:
            raise StopAsyncIteration


async def batched_interleave_longest(*iterators: AsyncIterator[_T]) -> AsyncIterator[Iterable[_T]]:
    current_generators = list(iterators)

    class _Empty:
        def __init__(self, reference: AsyncIterator[_T]):
            self.reference = reference

    while True:
        batch = [async_next(generator, _Empty(generator)) for generator in current_generators]
        results = []
        for coro in asyncio.as_completed(batch):
            result = await coro
            if isinstance(result, _Empty):
                current_generators.remove(result.reference)
            else:
                results.append(result)
        if not results:
            break
        yield iter(results)


async def make_iterable_async(iterable: Iterable[_T]) -> AsyncIterator[_T]:
    for nxt in iterable:
        yield nxt
