import asyncio
from typing import AsyncIterable, AsyncIterator, Iterable, TypeVar, Union, overload

_T = TypeVar("_T")
_VT = TypeVar("_VT", bound=object)


class _Sentinel:
    pass


__sentinel = _Sentinel()


@overload
async def async_next(iterator: AsyncIterator[_T]) -> _T:
    ...


@overload
async def async_next(iterator: AsyncIterator[_T], default: _VT) -> Union[_T, _VT]:
    ...


async def async_next(iterator: AsyncIterator[_T], default: Union[_VT, _Sentinel] = __sentinel) -> Union[_T, _VT]:
    task = asyncio.ensure_future(iterator.__anext__())
    try:
        return await task
    except StopAsyncIteration:
        if not isinstance(default, _Sentinel):
            return default
        else:
            raise StopAsyncIteration


async def async_interleave(*generators: AsyncIterator[_T]) -> AsyncIterator[Iterable[_T]]:
    current_generators = list(generators)
    while True:
        tmp = list(current_generators)
        results = []
        for generator in tmp:
            result = await async_next(generator, None)
            if result is None:
                current_generators.remove(generator)
            else:
                results.append(result)
        if not results:
            break
        yield iter(results)


async def make_async(iterable: Iterable[_T]) -> AsyncIterable[_T]:
    for nxt in iterable:
        yield nxt
