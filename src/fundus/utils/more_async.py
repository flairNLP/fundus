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


async def make_iterable_async(iterable: Iterable[_T]) -> AsyncIterator[_T]:
    for nxt in iterable:
        yield nxt
