import threading
from multiprocessing import Event, Queue
from multiprocessing.queues import Queue as tQueue
from queue import Empty
from typing import List, Iterable, Union

import more_itertools

from stream.layer import BaseLayer, ConsumerLayer
from stream.utils import each


class StreamLine:
    _Chainable = Union[BaseLayer, Queue]

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

    def _start(self):
        each(lambda x: x.start(), self.layers)

    def _handle_stream(self, tasks: Iterable):

        self._start()

        for task in tasks:
            self._task_queue.put(task)

        for layer in self.layers:
            layer.expire()
            layer.join()

        self._finished.set()

    def get_stream_handle(self, it):
        return threading.Thread(target=self._handle_stream, args=(it,))

    def map(self, it: Iterable):

        stream_handle = self.get_stream_handle(it)
        stream_handle.start()

        result = []

        while not self._finished.is_set():
            try:
                obj = self._result_queue.get(timeout=1)
                result.append(obj)
            except Empty:
                continue

        stream_handle.join()

        return result

    def imap(self, it: Iterable):

        stream_handle = self.get_stream_handle(it)
        stream_handle.start()

        while not self._finished.is_set():
            try:
                yield self._result_queue.get(timeout=1)
            except Empty:
                continue

        stream_handle.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        each(lambda x: x.join, self.layers)
