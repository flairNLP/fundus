import pickle
import traceback
from abc import ABC, abstractmethod
from functools import cache
from multiprocessing import Queue, Process, Event, Pipe
from queue import Empty
from typing import Callable, Optional, Union

import dill


class StreamProcess(Process, ABC):

    # noinspection PyShadowingBuiltins
    def __init__(self, target: Union[Callable, bytes], output: Queue = None, input: Queue = None, *args, **kwargs):

        # noinspection PyBroadException
        try:
            pickle.dumps(target)
        except Exception as err:
            target = dill.dumps(target)

        super(StreamProcess, self).__init__(target=target, *args, **kwargs)

        self.input: Optional[Queue] = input
        self.output: Optional[Queue] = output

        self._stop_event = Event()
        self._expire_event = Event()
        self._pipe_out, self._pipe_in = Pipe(duplex=False)
        self._exception = None

    @abstractmethod
    def _handle_job(self, job):
        raise NotImplementedError(f"'{type(self)} didn't implement '_handle_job'")

    # noinspection PyUnresolvedReferences
    @property
    @cache
    def target(self):
        if isinstance(self._target, bytes):
            return dill.loads(self._target)
        else:
            return self._target

    def run(self):

        assert self.input and self.output

        while True and not self.stopped:
            try:
                element = self.input.get(timeout=1)
                self._handle_job(element)
            except Empty:
                if self.expired:
                    break
            except Exception as exc:
                tb = traceback.format_exc()
                self._pipe_in.send((exc, tb))
                raise exc

    def stop(self):
        self._stop_event.set()

    @property
    def stopped(self) -> bool:
        return self._stop_event.is_set()

    def expire(self):
        """
        If called the process will terminate if the queue is empty, otherwise it will run till stop() is called
        """
        self._expire_event.set()

    @property
    def expired(self) -> bool:
        return self._expire_event.is_set()

    @property
    def exception(self) -> Optional[Exception]:
        if self._pipe_out.poll():
            self._exception = self._pipe_out.recv()
        return self._exception
