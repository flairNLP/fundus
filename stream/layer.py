from math import ceil
from multiprocessing import Queue
from typing import Callable, Optional, List, Type, Set

import more_itertools

from stream.process import StreamProcess
from stream.utils import each


class BaseLayer:

    def __init__(self, factory: Type[StreamProcess], target: Callable, size: int,
                 name: Optional[str] = None, max_queue_size: int = 50, output_size: Optional[int] = None):

        if not isinstance(factory, type(StreamProcess)):
            raise TypeError("factory must be of type 'StreamProcess'")

        if size < 1:
            raise ValueError("size of layer (num. process) must be at least 1")

        self.factory = factory
        self.target = target
        self.size = size
        self.name = name
        self.max_queue_size = max_queue_size
        self._output_size = output_size or size

        self._worker: List[StreamProcess] = [self.factory(target) for _ in range(size)]

    def _repopulate(self):
        in_queues = list(self.input)
        out_queues = list(self.output)
        self._worker = [self.factory(self.target) for _ in range(self.size)]
        self.input = in_queues
        self.output = out_queues

    @property
    def output_size(self) -> int:
        return len(self.output) if self.output else self._output_size

    @property
    def output(self) -> Set[Queue]:
        if self._worker:
            return {worker.output for worker in self._worker if worker.output}

    @output.setter
    def output(self, queues: List[Queue]):
        if len(queues) > len(self._worker):
            raise ValueError('Tried to assign more outputs than worker')

        chunk_size = ceil(len(self._worker) / len(queues))

        for i, chunk in enumerate(more_itertools.chunked(self._worker, chunk_size)):
            for worker in chunk:
                worker.output = queues[i]

    @property
    def input(self) -> Set[Queue]:
        if self._worker:
            return {worker.input for worker in self._worker if worker.input}

    @input.setter
    def input(self, queues: List[Queue]):
        if len(queues) > len(self._worker):
            raise ValueError('Tried to assign more inputs than worker')

        chunk_size = ceil(len(self._worker) / len(queues))

        for i, chunk in enumerate(more_itertools.chunked(self._worker, chunk_size)):
            for worker in chunk:
                worker.input = queues[i]

    def start(self):
        if self.terminated:
            self._repopulate()
        each(lambda x: x.start(), self._worker)

    def expire(self):
        each(lambda x: x.expire(), self._worker)

    def stop(self):
        each(lambda x: x.stop(), self._worker)

    def join(self):
        each(lambda x: x.join(), self._worker)

    @property
    def terminated(self):
        return bool([worker for worker in self._worker if worker.exitcode is not None])


class _Supplier(StreamProcess):

    def _handle_job(self, job):
        for obj in self.target(job):
            self.output.put(obj)


class _Unary(StreamProcess):

    def _handle_job(self, job):
        self.output.put(self.target(job))


class _Consumer(StreamProcess):
    def _handle_job(self, job):
        self.target(job)


class SupplyLayer(BaseLayer):

    def __init__(self, target: Callable, size: int, name: Optional[str] = None, max_queue_size: int = 50,
                 output_size: Optional[int] = None):
        super(SupplyLayer, self).__init__(_Supplier, target, size, name, max_queue_size, output_size)


class UnaryLayer(BaseLayer):

    def __init__(self, target: Callable, size: int, name: Optional[str] = None, max_queue_size: int = 50,
                 output_size: Optional[int] = None):
        super(UnaryLayer, self).__init__(_Unary, target, size, name, max_queue_size, output_size)


class ConsumerLayer(BaseLayer):

    def __init__(self, target: Callable, size: int, name: Optional[str] = None, max_queue_size: int = 50,
                 output_size: Optional[int] = None):
        super(ConsumerLayer, self).__init__(_Consumer, target, size, name, max_queue_size, output_size)
