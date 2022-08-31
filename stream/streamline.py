import traceback
from abc import ABC
from multiprocessing import Queue, Process, Event, Pipe, Manager
from queue import Empty
from typing import Callable, Optional, List, Literal, Dict, Type, Iterable, Collection

import more_itertools

import threading


def _each(fn: Callable, it: Iterable):
    for x in it:
        fn(x)


class StreamProcess(Process, ABC):

    def __init__(self, output: Queue = None, input: Queue = None, *args, **kwargs):
        super(StreamProcess, self).__init__(*args, **kwargs)
        self.input: Optional[Queue] = input
        self.output: Optional[Queue] = output


class Supplier(StreamProcess):

    def __init__(self, target: Callable, args: tuple = None, kwargs: dict = None):
        args = tuple() if not args else args
        kwargs = dict() if not args else kwargs
        super(Process, self).__init__(target=target, args=args, kwargs=kwargs)

    def run(self):

        assert self.output

        if self._target:
            for obj in self._target(*self._args, **self._kwargs):
                self.output.put(obj)


class _StoppableProcess(StreamProcess):

    def __init__(self, *args, **kwargs):
        super(_StoppableProcess, self).__init__(*args, **kwargs)
        self._stop_event = Event()

    def stop(self):
        self._stop_event.set()

    @property
    def stopped(self) -> bool:
        return self._stop_event.is_set()


class Consumer(_StoppableProcess):

    def __init__(self, target: Callable, args: tuple = None, kwargs: dict = None):

        args = tuple() if not args else args
        kwargs = dict() if not args else kwargs
        super(Process, self).__init__(target=target, args=args, kwargs=kwargs)
        self.input: Optional[Queue] = None
        self._expire_event = Event()
        self._pipe_out, self._pipe_in = Pipe(duplex=False)
        self._exception = None

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

    def run(self):

        assert self.input and self.output

        while True and not self.stopped:
            try:
                element = self.input.get(timeout=1)
                result = self._target(element)
                self.output.put(result)
                # TODO: find something faster than Queue.task_done()
                # self._input.task_done()
            except Empty:
                if self.expired:
                    break
            except Exception as exc:
                tb = traceback.format_exc()
                self._pipe_in.send((exc, tb))
                raise exc


class StreamLayer:

    def __init__(self, factory: Type[StreamProcess], args: Iterable, target: Callable, size: int,
                 name: Optional[str], max_queue_size: int = 10, output_size: Optional[int] = None):

        if not isinstance(factory, type(StreamProcess)):
            raise TypeError("factory must be of type 'StreamProcess'")

        if size < 1:
            raise ValueError("size of layer (num. process) must be at least 1")

        self.factory = factory
        self.target = target
        self.size = size
        self.name = name
        self.max_queue_size = max_queue_size
        self.output_size = output_size

        self._output: List[Queue] = [Queue(maxsize=self.max_queue_size) for _ in range(output_size or size)]

        self._worker: List[StreamProcess]
        if args:
            self._worker = [self.factory(target=target, args=(it,)) for it in args]
        else:
            self._worker = [self.factory(target=target)]

    @property
    def output(self) -> List[Queue]:
        return self._output

    @property
    def input(self) -> Optional[List[Queue]]:
        if self._worker:
            return [worker.input for worker in self._worker]

    def start(self):
        _each(lambda x: x.start, self._worker)

    def expire(self):
        _each(lambda x: x.expire, self._worker)

    def stop(self):
        _each(lambda x: x.stop, self._worker)

    def join(self):
        _each(lambda x: x.join, self._worker)

    def connect_to(self, queues: List[Queue]):
        for i, chunk in enumerate(more_itertools.chunked(self._worker, len(queues))):
            for worker in chunk:
                worker.input = queues[i]

    def set_output(self, queues: List[Queue]):
        for i, chunk in enumerate(more_itertools.chunked(self._worker, len(queues))):
            for worker in chunk:
                worker.output = queues[i]


class StreamLine:

    def __init__(self,
                 layers: List[StreamLayer],
                 disable_output: bool = False):
        self.layers = layers
        self._disable_output = disable_output

        self._task_queue = Queue()

        # setup grid
        layers[0].connect_to([self._task_queue])
        for current, nxt in more_itertools.windowed(self.layers, 2):
            nxt.connect_to(current.output)

    def _start_layers(self):
        _each(lambda x: x.start, self.layers)

    def _handle(self, tasks: Iterable):
        for task in tasks:
            self._task_queue.put(task)

    def feed(self, it: Iterable):

        result_queue = Queue()

        self._start_layers()

        while True:
            result =

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _each(lambda x: x.join, self.layers)
