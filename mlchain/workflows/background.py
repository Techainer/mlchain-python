from threading import Thread, Event
import inspect
from mlchain.workflows.task import Task
import trio 

class BackgroundTask(Thread):
    def __init__(self, interval, task, max_repeat):
        assert callable(task)

        Thread.__init__(self)
        self.stopped = Event()
        self.interval = interval
        self.task = task
        self.max_repeat = max_repeat

    def stop(self):
        self.stopped.set()
        self.join()

    def run(self):
        if self.interval is not None:
            count_repeat = 0
            while (self.max_repeat < 0 or count_repeat < self.max_repeat) and (not self.stopped.wait(self.interval.total_seconds())):
                if inspect.iscoroutinefunction(self.task) or isinstance(type(self.task), Task) or issubclass(type(self.task), Task):
                    trio.run(self.task)
                else:
                    self.task()
                count_repeat += 1
        else:
            if inspect.iscoroutinefunction(self.task) or isinstance(type(self.task), Task) or issubclass(type(self.task), Task):
                trio.run(self.task)
            else:
                self.task()

class Background:
    """
    Run a task in background using Threading.Event
    :task: [Task, function] item
    :interval: 
    """

    def __init__(self, task, interval=None, max_repeat=-1):
        assert callable(task), 'You have to transfer a callable instance or an mlchain.Task'

        self.task = task 
        self.interval = interval
        self.max_repeat = max_repeat

    def run(self):
        task = BackgroundTask(interval=self.interval, task=self.task, max_repeat=self.max_repeat)
        task.start()
