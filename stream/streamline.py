import traceback
from multiprocessing import Queue, Process, Event, Pipe
from queue import Empty
from typing import Callable, Optional


class FunctionalPart(Process):

    def __init__(self, *args, **kwargs):
        super(FunctionalPart, self).__init__(*args, **kwargs)


class Supplier(FunctionalPart):

    def __init__(self, target: Callable, args: tuple = None, kwargs: dict = None):
        args = tuple() if not args else args
        kwargs = dict() if not args else kwargs
        super(Process, self).__init__(target=target, args=args, kwargs=kwargs)
        self._output: Optional[Queue] = None

    @property
    def output(self):
        return self._output

    def run(self):

        assert self.output

        if self._target:
            for obj in self._target(*self._args, **self._kwargs):
                self.output.put(obj)


class _StoppableProcess(FunctionalPart):

    def __init__(self, *args, **kwargs):
        super(_StoppableProcess, self).__init__(*args, **kwargs)
        self._stop_event = Event()

    def stop(self):
        self._stop_event.set()

    @property
    def stopped(self):
        return self._stop_event.is_set()


class Consumer(_StoppableProcess):

    def __init__(self, target: Callable, args: tuple = None, kwargs: dict = None):

        args = tuple() if not args else args
        kwargs = dict() if not args else kwargs
        super(Process, self).__init__(target=target, args=args, kwargs=kwargs)
        self._input: Optional[Queue] = None
        self._output: Optional[Queue] = None
        self._expire_event = Event()
        self._pipe_out, self._pipe_in = Pipe(duplex=False)
        self._exception = None

    def expire(self):
        """
        If called the process will terminate if the queue is empty, otherwise it will run till stop() is called
        """
        self._expire_event.set()

    @property
    def input(self) -> Queue:
        return self._input

    @property
    def output(self) -> Queue:
        return self._output

    @property
    def expired(self):
        return self._expire_event.is_set()

    @property
    def exception(self):
        if self._pipe_out.poll():
            self._exception = self._pipe_out.recv()
        return self._exception

    def run(self):

        assert self.input and self.output

        while True and not self.stopped:
            try:
                element = self._input.get(timeout=1)
                result = self._target(element)
                self._output.put(result)
                # TODO: find something faster than Queue.task_done()
                # self._input.task_done()
            except Empty:
                if self.expired:
                    break
            except Exception as exc:
                tb = traceback.format_exc()
                self._pipe_in.send((exc, tb))
                raise exc


class StreamPart:

    def __init__(self, func: FunctionalPart, amount: int):
        self.func = func
        self.amount = amount
