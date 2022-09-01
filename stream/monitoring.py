import curses
import multiprocessing
import threading
import time
from io import StringIO
from multiprocessing.connection import Connection
from multiprocessing.queues import JoinableQueue
from typing import Callable, Any, Iterable, List


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

# def _get_monitor(self, stream_queues, producers, consumer_storage, stdout, stderr) -> _Monitor:
#
#     def create_lines() -> List[str]:
#         return [
#             f"stream occupancy: {', '.join([f'{(s.qsize() / self._max_queue_size):.2%}%' for s in stream_queues])}",
#             f"assigned processes: {', '.join([f'{len(c)}' for _, c in consumer_storage.mapping.items()])}",
#             f"result occupancy: {(self._result_queue.qsize() / self._max_queue_size):3.2%}",
#             f"producers: {len(producers)}",
#             f"consumers: {len(consumer_storage)}",
#             f"total objects processed: {self._result_queue.completed_tasks}",
#             f"elapsed time: {self._result_queue.elapsed_time:.2f} seconds",
#             f"throughput: {self._result_queue.throughput:5.2f} objects/sec",
#             f"avg: {self._result_queue.avg:5.2f}",
#             f"producers alive: {len([p for p in producers if p.is_alive()])}",
#             f"consumers alive: {len([p for p in consumer_storage if p.is_alive()])}"]
#
#     return _Monitor(target=create_lines, delay=0.1, stdout=stdout, stderr=stdout)
