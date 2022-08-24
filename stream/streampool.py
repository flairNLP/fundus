import curses
import multiprocessing
import sys
import threading
import time
import traceback
from io import StringIO
from math import ceil, floor
from multiprocessing import Manager, Process, cpu_count, Pipe
from multiprocessing import Queue as ctxQueue
from multiprocessing.connection import Connection
from multiprocessing.queues import Queue, JoinableQueue
from queue import Empty
from typing import Callable, Any, Generator, Tuple, Iterable, List, Collection, Dict, Iterator

import dill
import more_itertools
# utils

class IOPipe(StringIO):
    def __init__(self, pipe):
        super(IOPipe, self).__init__()
        self.pipe = pipe

    def write(self, s):
        self.pipe.send(s.strip())


class FIFOBuffer:

    def __init__(self, max_size):
        self.max_size = max_size
        self._current_size: int = 0
        self._fifo_list: List[Any] = []

    def push(self, objects: Iterable[Any]) -> None:
        for o in objects:
            if self._current_size == self.max_size:
                self._fifo_list.pop(0)
            else:
                self._current_size += 1
            self._fifo_list.append(o)

    @property
    def content(self) -> List[Any]:
        return self._fifo_list


# threads
class _StoppableThread(threading.Thread):
    # class StoppableThread form https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, *args, **kwargs):
        super(_StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class _TimedThread(_StoppableThread):
    """
    This thread executes <target> every <delay> seconds.
    """

    def __init__(self, target, delay, *args, **kwargs):
        super(_TimedThread, self).__init__(*args, **kwargs)
        self.delay = delay
        self._target = target
        self._args = args
        self._kwargs = kwargs

    def run(self):
        next_time = time.time() + self.delay
        try:
            while True and not self.stopped():
                time.sleep(max(0, next_time - time.time()))
                if self._target:
                    self._target(*self._args, **self._kwargs)
                next_time += (time.time() - next_time) // self.delay * self.delay + self.delay
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self._target, self._args, self._kwargs


class _Monitor(_StoppableThread):

    def __init__(self, target: Callable[[], List[str]], delay, stdout: Connection, stderr: Connection,
                 std_buffer_size: int = 1000):
        super(_Monitor, self).__init__()
        self._delay = delay
        self._target = target
        self._std_buffer_site = std_buffer_size
        self._stdout = stdout
        self._stderr = stderr
        self._stderr_buffer = FIFOBuffer(max_size=std_buffer_size)
        self._stdout_buffer = FIFOBuffer(max_size=std_buffer_size)

    def update_screen(self, lns: List[str]):
        rows = curses.LINES
        cols = curses.COLS

        monitor_size = (11, cols - 1)
        err_size = (monitor_size[0] + 2, cols - 1)

        monitor_win = curses.newwin(*monitor_size, 0, 0)
        err_pad = curses.newpad(self._stderr_buffer.max_size, cols - 1)

        monitor_win.erase()
        for i, ln in enumerate(lns):
            monitor_win.addstr(i, 0, ln)
        monitor_win.refresh()

        if content := self._stderr_buffer.content:
            err_pad.erase()
            for i, ln in enumerate(content):
                err_pad.addstr(i, 0, ln)
            err_pad.refresh(len(content) - rows + err_size[0], 0, err_size[0], 0, rows - 1, err_size[1])

    def main(self, stdscr):
        stdscr.keypad(True)
        next_time = time.time() + self._delay
        try:
            while True and not self.stopped():
                time.sleep(max(0, next_time - time.time()))

                key = stdscr.getch()
                if key == ord('q'):
                    break
                print('hallo')

                # fill buffers
                if self._stdout.poll():
                    count = 0
                    while ln := self._stdout.recv().strip() and count < 50:
                        self._stdout_buffer.push(ln)
                        count += 1
                if self._stderr.poll():
                    count = 0
                    while ln := self._stderr.recv().strip() and count < 50:
                        self._stderr_buffer.push(ln)
                        count += 1

                lines = self._target()
                self.update_screen(lines)

                next_time += (time.time() - next_time) // self._delay * self._delay + self._delay
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self._target

    def run(self):
        curses.wrapper(self.main)


# processes
class _StoppableProcess(Process):
    """
    Same as _StoppableThread
    """

    def __init__(self, *args, **kwargs):
        super(_StoppableProcess, self).__init__(*args, **kwargs)
        self._stop_event = multiprocessing.Event()

    def stop(self):
        self._stop_event.set()

    @property
    def stopped(self):
        return self._stop_event.is_set()


class _Producer(Process):

    def __init__(self, target: Callable[[Queue, ...], None], args, max_queue_size=100):
        super(_Producer, self).__init__()
        self._target = target
        self._args = args
        self._output = Queue(maxsize=max_queue_size, ctx=multiprocessing.get_context())

    def run(self):
        if isinstance(self._target, bytes):
            self._target = dill.loads(self._target)
        self._target(self._output, *self._args)

    @property
    def output(self) -> Queue:
        return self._output


class _Consumer(_StoppableProcess):

    def __init__(self, target: Callable[[Any], Any], input_queue: Queue, output_queue: Queue):
        """
        Consumer process consuming elements from the stream and enqueue the results.
        For simplicity, we overwrite BaseProcess _target, _args, _kwargs, so for now it isn't possible, in the scope
        of this consumer process, to target a function with additional parameters rather than the specified enqueued
        element this can  be somehow easily changed by passing down function args, kwargs and using BaseProcess
        attributes, but for now
        The consumer runs either till stop() or expire() is called.
        When stop() is called, the consumer will terminate after processing the current queue element,
        when expire() is called the consumer will terminate with the next Queue.Empty. This doesn't necessarily mean
        that the queue remains empty, only iff the producer already terminated
        """
        super(_Consumer, self).__init__()
        self._input = input_queue
        self._output = output_queue
        self._target = target
        self._expire_event = multiprocessing.Event()
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
        if isinstance(self._target, bytes):
            self._target = dill.loads(self._target)
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


# Queues
class TaskMonitor:

    def __init__(self):
        self._time = time.time()
        self._current_throughput: float = 0
        self._current_load: int = 0
        self._completed_tasks: int = 0
        self._elapsed_time: float = 0

    @property
    def throughput(self) -> float:
        return self._current_throughput

    @property
    def completed_tasks(self) -> int:
        return self._completed_tasks

    @property
    def elapsed_time(self) -> float:
        return self._elapsed_time + (time.time() - self._time)

    def task(self):
        self._current_load += 1
        self._completed_tasks += 1

    def tick(self):
        delta = time.time() - self._time
        self._time += delta
        self._elapsed_time += delta
        self._current_throughput = self._current_load / delta
        self._current_load = 0


class MonitoredQueue(JoinableQueue):

    def __init__(self, maxsize=0, ctx=None):
        ctx = multiprocessing.get_context() if not ctx else ctx
        super(MonitoredQueue, self).__init__(maxsize=maxsize, ctx=ctx)
        self._monitor: TaskMonitor = TaskMonitor()

    @property
    def throughput(self) -> float:
        self._monitor.tick()
        return self._monitor.throughput

    @property
    def completed_tasks(self):
        return self._monitor.completed_tasks

    @property
    def elapsed_time(self):
        return self._monitor.elapsed_time

    @property
    def avg(self) -> float:
        return self.completed_tasks / self.elapsed_time

    def task_done(self) -> None:
        super(MonitoredQueue, self).task_done()
        self._monitor.task()


class QueueConsumer:
    """
    This class provides basic functionality to consume a stream/feed via multiprocessing while being capable of
    adjusting the number of used processes dynamically. The design follows a producer consumer pattern.
    Given a
        feeder_function, specified as a function which feeds a queue given through func args
        f[queue] -> None
        i.e:
        def feed(queue: Queue) -> None:
            ...
            for el in stream:
                queue.put(el)
    and a
        consumer_function, specified as a function that receives an element from the queue (and returns something)
        f[Any] -> Any
        i.e:
        def consume(element: Any) -> Any:
            result = process(element)
            return element
    self.consume_feed will return a generator that yields the processed queue elements.
    This class is capable of dynamically adjust the number of consumer processes to the payload based on queue
    occupation: (in Detail: if input queue is 75% occupied a new consumer process will spawn, if input queue
    is less than 25% occupied, the last started consumer process will stop after finishing the current task)

    After the feed is empty, this class will determine and join all remaining processes and return to the
    main process
    """

    class ConsumerStorage:

        def __init__(self):
            self._mapping: Dict[Queue, List[_Consumer]] = {}

        @staticmethod
        def _map(consumer: _Consumer):
            return consumer.input

        @property
        def mapping(self) -> Dict[Queue, List[_Consumer]]:
            return self._mapping

        @property
        def consumers(self) -> Iterator:
            return more_itertools.flatten(self._mapping.values())

        def add(self, consumer: _Consumer):
            if not (tmp := self._mapping.get(_m := self._map(consumer), [])):
                self.mapping[_m] = tmp
            tmp.append(consumer)

        def remove(self, consumer: _Consumer):
            self._mapping[self._map(consumer)].remove(consumer)

        def __getitem__(self, item):
            return self.mapping[self._map(item)]

        def __iter__(self) -> Iterator[_Consumer]:
            return iter(self.consumers)

        def __len__(self):
            return len(list(self.consumers))

        def __copy__(self):
            cls = self.__class__
            result = cls.__new__(cls)
            result.__dict__.update(self.__dict__)
            return result

    def __init__(self, max_queue_size: int = 200):
        """
        :param max_queue_size: Maximal inpout/output qsize
        """
        self._max_queue_size = max_queue_size
        self._manager = Manager()
        self._stream_queues: List[Queue] = []
        self._result_queue = MonitoredQueue(maxsize=self._max_queue_size)
        self._NUMBER_OF_CPUs = cpu_count()

    @staticmethod
    def _get_consumer_handler(storage: ConsumerStorage, spawn: Callable[[Queue], _Consumer]) -> _TimedThread:

        number_of_consumers = len(storage)
        number_of_queues = len(storage.mapping.keys())

        def handle_processes():

            # collect garbage
            for p in storage.__copy__():
                if not p.is_alive():
                    p.join()
                    storage.remove(p)

            # spawn new processes
            seq = [0] * number_of_queues
            for i in range(number_of_consumers):
                seq[i % number_of_queues] += 1

            for i, (queue, consumers) in enumerate(storage.mapping.items()):
                for _ in range(seq[i] - len(consumers)):
                    new_consumer = spawn(queue)
                    consumers.append(new_consumer)
                    new_consumer.start()

        return _TimedThread(target=handle_processes, delay=0.1)

    def _get_monitor(self, stream_queues, producers, consumer_storage, stdout, stderr) -> _Monitor:

        def create_lines() -> List[str]:
            return [
                f"stream occupancy: {', '.join([f'{(s.qsize() / self._max_queue_size):.2%}%' for s in stream_queues])}",
                f"assigned processes: {', '.join([f'{len(c)}' for _, c in consumer_storage.mapping.items()])}",
                f"result occupancy: {(self._result_queue.qsize() / self._max_queue_size):3.2%}",
                f"producers: {len(producers)}",
                f"consumers: {len(consumer_storage)}",
                f"total objects processed: {self._result_queue.completed_tasks}",
                f"elapsed time: {self._result_queue.elapsed_time:.2f} seconds",
                f"throughput: {self._result_queue.throughput:5.2f} objects/sec",
                f"avg: {self._result_queue.avg:5.2f}",
                f"producers alive: {len([p for p in producers if p.is_alive()])}",
                f"consumers alive: {len([p for p in consumer_storage if p.is_alive()])}"]

        return _Monitor(target=create_lines, delay=0.1, stdout=stdout, stderr=stdout)

    def consume_feed(self,
                     feeder: Tuple[Callable[[Queue], None], Collection],
                     consumer_function: Callable[[Any], Any],
                     max_process: int = None,
                     dynamic: bool = False,
                     monitoring: bool = False) -> Generator[Any, None, None]:

        """
        This function consumes the given feed with a consumer function and returns a generator over the computed
        results. In the future maybe there will be an option to skipp return.
        If the given consumer_function is serialized it will be unpacked using dill.loads.

        :param monitoring: If true enables monitoring output on stdout via curse. It's highly recommended that nothing
            else gets written to stdout while monitoring is enabled
        :param feeder: A callable feeding a queue.Queue given as a function parameter
        :param consumer_function: A callable or dill serialized callable
        :param max_process: Optional cap of parallel running consumer processes
        :param dynamic: If True, additional consumer processes will be spawned and terminated based on queue load.
            See class description.
        :return:
        """

        if not max_process:
            max_process = self._NUMBER_OF_CPUs

        if max_process < 2:
            raise AssertionError(f'Minimal number of process to give is 2, current: {max_process}.'
                                 f'Either the specified value or your cpu count ({self._NUMBER_OF_CPUs}) is too low '
                                 f'or the given <max_process> parameter is specified to low')
        elif len(feeder[1]) > floor(max_process / 2):
            raise AssertionError(f'Maximal number of feeding process to spawn has to be <= floor(max_process/2)')

        def spawn_consumer(queue) -> _Consumer:
            return _Consumer(target=consumer_function,
                             input_queue=queue,
                             output_queue=self._result_queue)

        # setup streams
        stream_queues = [ctxQueue(maxsize=self._max_queue_size) for _ in feeder[1]]
        producers = [Process(target=feeder[0], args=(queue, it)) for queue, it in zip(stream_queues, feeder[1])]

        # setup consumers
        consumer_storage = self.ConsumerStorage()
        number_of_consumers = max_process - len(producers) if not dynamic else len(producers)
        queue_seq = list(more_itertools.ncycles(
            stream_queues, ceil(number_of_consumers / len(producers))
        ))[:number_of_consumers]
        for queue in queue_seq:
            consumer_storage.add(spawn_consumer(queue))

        # setup process handlers
        consumer_handler = self._get_consumer_handler(consumer_storage, spawn_consumer)

        # start all process
        for process in producers:
            process.start()
        for process in consumer_storage:
            process.start()
        consumer_handler.start()

        while True:
            try:
                result = self._result_queue.get(timeout=1)
                yield result
                self._result_queue.task_done()
            except Empty:
                if any(process.is_alive() for process in producers):
                    continue
                else:
                    consumer_handler.stop()
                    consumer_handler.join()
                    for process in [process for process in consumer_storage if not process.expired]:
                        process.expire()
                    if [process for process in consumer_storage if process.is_alive()]:
                        continue
                    else:
                        break

        for process in producers:
            process.join()
        for process in consumer_storage:
            process.join()