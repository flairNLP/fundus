import threading
from contextlib import contextmanager
from multiprocessing import Event, Queue
from multiprocessing.queues import Queue as tQueue
from queue import Empty
from typing import List, Iterable, Union

import more_itertools

from stream.layer import BaseLayer, ConsumerLayer
from stream.utils import each


class StreamLine:
    _Chainable = Union[BaseLayer, tQueue]

    def __init__(self,
                 layers: List[BaseLayer],
                 disable_output: bool = False):
        self.layers = layers
        self._disable_output = disable_output

        self._task_queue = Queue()
        self._result_queue = Queue()

        # setup grid
        self.chain(self.layers[0], self._task_queue)

        for cur, nxt in more_itertools.windowed(self.layers, 2):
            self.chain(nxt, cur)

        if not (disable_output or isinstance(self.layers[-1], ConsumerLayer)):
            self.chain(self._result_queue, self.layers[-1])

        self._running = Event()
        self._finished = Event()

    @staticmethod
    def chain(source: _Chainable, target: _Chainable):
        # TODO: refactor

        if type(source) == type(target) != BaseLayer:
            raise TypeError(f"It is not allowed to chain two {type(source)}")

        # connect <source> -> <target>
        # case 1: Layer -> Queue
        if isinstance(source, BaseLayer) and isinstance(target, tQueue):
            source.input = [target]

        # case 2: Queue -> Layer
        elif isinstance(source, tQueue) and isinstance(target, BaseLayer):
            target.output = [source]

        # case 3: Layer -> Layer
        elif isinstance(source, BaseLayer) and isinstance(target, BaseLayer):
            queues = [Queue(maxsize=target.max_queue_size) for _ in range(min(target.output_size, source.size))]
            target.output = queues
            source.input = queues

        else:
            raise TypeError(f"{target if isinstance(source, (BaseLayer, tQueue)) else source} is not chainable")

    @contextmanager
    def _start(self, it):
        if self._running.is_set():
            self._finished.wait()
        stream_handle = self._get_stream_handle(it)
        try:
            stream_handle.start()
            yield
        finally:
            stream_handle.join()
            del stream_handle

    def _handle_stream(self, tasks: Iterable):

        self._running.set()
        self._finished.clear()

        # start layers consecutively
        each(lambda x: x.start(), self.layers)

        for task in tasks:
            self._task_queue.put(task)

        for layer in self.layers:
            layer.expire()
            layer.join()

        self._running.clear()
        self._finished.set()

    def _get_stream_handle(self, it):
        return threading.Thread(target=self._handle_stream, args=(it,))

    def map(self, it: Iterable):

        result = []

        with self._start(it):
            while True:
                try:
                    obj = self._result_queue.get(timeout=1)
                    result.append(obj)
                except Empty:
                    if self._finished.is_set():
                        break
                    continue

        return result

    def imap(self, it: Iterable):

        with self._start(it):
            while True:
                try:
                    yield self._result_queue.get(timeout=1)
                except Empty:
                    if self._finished.is_set():
                        break
                    continue

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for layer in self.layers:
            if not layer.terminated:
                raise AssertionError(f"{layer.name or layer.__class__.__name__} isn't fully terminated. Potential leak.")
