import asyncio
from asyncio import AbstractEventLoop
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


class ManagedEventLoop:
    def __init__(self) -> None:
        self.event_loop: AbstractEventLoop

    def __enter__(self) -> AbstractEventLoop:
        try:
            asyncio.get_running_loop()
            raise AssertionError()
        except RuntimeError:
            self.event_loop = asyncio.new_event_loop()
        except AssertionError:
            raise RuntimeError(
                "There is already an event loop running. If you want to crawl articles inside an "
                "async environment use crawl_async() instead."
            )
        return self.event_loop

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.event_loop.run_until_complete(self.event_loop.shutdown_asyncgens())
        self.event_loop.close()
