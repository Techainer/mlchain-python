import inspect
import time
from threading import Thread, Event
import trio
from .task import Task
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import logging 
import traceback 

class BackgroundTask(Thread):
    def __init__(self, interval, task, max_repeat, callback=None, max_thread:int=1, pass_fail_job:bool=False):
        assert callable(task)

        Thread.__init__(self)
        self.stopped = Event()
        self.is_done = False
        self.interval = interval
        self.task = task
        self.max_repeat = max_repeat
        self.callback = callback
        self.output = None 
        self.pool_limit = ThreadPoolExecutor(max_workers=max_thread)
        self.pass_fail_job = pass_fail_job 

        if callback is not None:
            self.pool_limit_callback = ThreadPoolExecutor(max_workers=1)

    def stop(self):
        self.stopped.set()
        self.join()

    def get_output(self, task, *args, **kwargs): 
        try:
            self.output = task(*args, **kwargs)
        except Exception as ex: 
            self.output = ("MLCHAIN_BACKGROUND_ERROR", traceback.format_exc())
        self.call_the_callback()

    def call_the_callback(self): 
        if self.callback:
            self.pool_limit_callback.submit(self.callback)

        if isinstance(self.output, tuple) and len(self.output) == 2 and self.output[0] == "MLCHAIN_BACKGROUND_ERROR": 
            if self.pass_fail_job: 
                logging.error("BACKGROUND CALL ERROR: {0}".format(self.output[1]))
            else: 
                raise Exception("BACKGROUND CALL ERROR: {0}".format(self.output[1]))

    def run(self):
        if self.interval is not None:
            count_repeat = 0
            while (self.max_repeat < 0 or count_repeat < self.max_repeat) \
                    and (not self.stopped.wait(self.interval.total_seconds())):

                if isinstance(type(self.task), Task) \
                    or issubclass(type(self.task), Task):
                        if inspect.iscoroutinefunction(self.task.func_): 
                            self.pool_limit.submit(self.get_output, trio.run, self.task)
                        else:
                            self.pool_limit.submit(self.get_output, self.task.func_, *self.task.args, **self.task.kwargs)
                else: 
                    if inspect.iscoroutinefunction(self.task):
                        self.pool_limit.submit(self.get_output, trio.run, self.task)
                    else:
                        self.pool_limit.submit(self.get_output, self.task)
                count_repeat += 1
        else:
            if isinstance(type(self.task), Task) \
                    or issubclass(type(self.task), Task):
                        if inspect.iscoroutinefunction(self.task.func_): 
                            self.pool_limit.submit(self.get_output, trio.run, self.task)
                        else:
                            self.pool_limit.submit(self.get_output, self.task.func_, *self.task.args, **self.task.kwargs)
            else: 
                if inspect.iscoroutinefunction(self.task): 
                    self.pool_limit.submit(self.get_output, trio.run, self.task)
                else:
                    self.pool_limit.submit(self.get_output, self.task)
        
        self.pool_limit.shutdown(wait=True)
        self.is_done = True

        if isinstance(self.output, tuple) and len(self.output) == 2 and self.output[0] == "MLCHAIN_BACKGROUND_ERROR": 
            if self.pass_fail_job: 
                logging.error("BACKGROUND CALL ERROR: {0}".format(self.output[1]))
            else: 
                raise Exception("BACKGROUND CALL ERROR: {0}".format(self.output[1]))
            
        if self.callback is not None:
            self.pool_limit_callback.shutdown(wait=True)
        self.is_done = True

    def wait(self, interval: float = 0.1):
        while not self.is_done:
            time.sleep(interval)
        return self.output

    def wait(self, interval: float = 0.1):
        while not self.is_done:
            time.sleep(interval)
        return self.output

class Background:
    """
    Run a task in background using Threading.Event
    :task: [Task, function] item
    :interval: timedelta or float seconds
    """

    def __init__(self, task, interval:float=None, max_repeat:int=-1, callback=None):
        assert callable(task), 'You have to transfer a callable instance or an mlchain.Task'
        assert (max_repeat > 0 and interval is not None and interval > 0) or max_repeat == -1, "interval need to be set when max_repeat > 0"
        assert callback is None or callable(callback), "callback need to be callable"

        if interval is not None: 
            if isinstance(interval, int) or isinstance(interval, float): 
                interval = timedelta(seconds = interval)
        
        self.task = task
        self.interval = interval
        self.max_repeat = max_repeat
        self.callback = callback

    def run(self, max_thread:int=1, pass_fail_job:bool=False):
        task = BackgroundTask(interval=self.interval, task=self.task,
                              max_repeat=self.max_repeat, callback=self.callback, max_thread=max_thread, pass_fail_job=pass_fail_job)
        task.start()

        return task