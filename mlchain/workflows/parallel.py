import trio 
import inspect
from mlchain.base.log import logger
from multiprocessing.pool import ThreadPool
from mlchain.base.log import format_exc, except_handler
import os

class TrioProgress(trio.abc.Instrument):

    def __init__(self, total, notebook_mode=False, **kwargs):
        if notebook_mode:
            from tqdm.notebook import tqdm
        else:
            from tqdm import tqdm

        self.tqdm = tqdm(total=total, **kwargs)

    def task_processed(self):
        self.tqdm.update(1)

class Parallel:
    """
    Build a collection of tasks to be executed in parallel
    :tasks: List of [Task, function] items
    :max_threads: Maximum Threads for this Parallel 
    :max_retries: Maximum retry time when a task fail 
    :pass_fail_job: Pass or Raise error when a task run fail 
    :verbose: Print error or not 
    """

    def __init__(self, tasks:[], max_threads:int=10, max_retries:int=0, pass_fail_job:bool=False, verbose:bool=True, threading:bool=True):
        """
        :tasks: [Task, function] items
        :max_threads: Maximum threads to Parallel, max_threads=0 means no limitation 
        :max_retries: How many time retry when job fail
        :pass_fail_job: No exeption when a job fail 
        :verbose: Verbose or not 
        """

        assert isinstance(tasks, list) and all(callable(task) for task in tasks), 'You have to transfer a list of callable instances or mlchain.Task'
        self.tasks = tasks
        if max_threads == -1:
            max_threads = 100
        elif max_threads == 0:
            max_threads = os.cpu_count()
        self.max_threads = max(0, max_threads)
        self.threading = threading
        if self.max_threads > 0:
            self.limiter = trio.CapacityLimiter(self.max_threads)
        else:
            self.limiter = None

        self.max_retries = max(max_retries + 1, 1)
        self.pass_fail_job = pass_fail_job
        self.verbose = verbose
        self.show_progress_bar = False

    def update_progress_bar(self):
        if self.show_progress_bar:
            self.progress_bar.task_processed()

    async def __call_sync(self, task, outputs, idx, limiter, max_retries=1, pass_fail_job=False):
        if limiter is not None:
            async with limiter:
                for retry_idx in range(max_retries):
                    try:
                        outputs[idx] = task()
                        self.update_progress_bar()
                        return None
                    except Exception as ex:
                        if retry_idx == max_retries - 1 and not pass_fail_job:
                            with except_handler():
                                raise AssertionError("ERROR in {}th task\n".format(idx) + format_exc(name='mlchain.workflows.parallel'))
                        elif retry_idx < max_retries - 1 or not self.verbose:
                            logger.error("PARALLEL ERROR in {0}th task and retry task, run times = {1}".format(idx, retry_idx + 1))
                        else:
                            logger.debug("PASSED PARALLEL ERROR in {}th task:".format(idx) + format_exc(name='mlchain.workflows.parallel'))
        else:
            for retry_idx in range(max_retries):
                try:
                    outputs[idx] = task()
                    self.update_progress_bar()
                    return None
                except Exception as ex:
                    if retry_idx == max_retries - 1 and not pass_fail_job:
                        with except_handler():
                            raise AssertionError("ERROR in {}th task\n".format(idx) + format_exc(name='mlchain.workflows.parallel'))
                    elif retry_idx < max_retries - 1 or not self.verbose:
                        logger.error("PARALLEL ERROR in {0}th task and retry task, run times = {1}".format(idx, retry_idx + 1))
                    else:
                        logger.debug("PASSED PARALLEL ERROR:", format_exc(name='mlchain.workflows.parallel'))
        self.update_progress_bar()

    async def __call_async(self, task, outputs, idx, limiter, max_retries=1, pass_fail_job=False):
        if limiter is not None:
            async with limiter:
                for retry_idx in range(max_retries):
                    try:
                        outputs[idx] = await task()
                        self.update_progress_bar()
                        return None
                    except Exception as ex:
                        if retry_idx == max_retries - 1 and not pass_fail_job:
                            with except_handler():
                                raise AssertionError("ERROR in {}th task\n".format(idx) + format_exc(name='mlchain.workflows.parallel'))
                        elif retry_idx < max_retries - 1 or not self.verbose:
                            logger.error("PARALLEL ERROR in {0}th task and retry task, run times = {1}".format(idx, retry_idx + 1))
                        else:
                            logger.debug("PASSED PARALLEL ERROR in {}th task:".format(idx) + format_exc(name='mlchain.workflows.parallel'))
        else:
            for retry_idx in range(max_retries):
                try:
                    outputs[idx] = await task()
                    self.update_progress_bar()
                    return None
                except Exception as ex:
                    if retry_idx == max_retries - 1 and not pass_fail_job:
                        with except_handler():
                            raise AssertionError("ERROR in {}th task\n".format(idx) + format_exc(name='mlchain.workflows.parallel'))
                    elif retry_idx < max_retries - 1 or not self.verbose:
                        logger.error("PARALLEL ERROR in {0}th task and retry task, run times = {1}".format(idx, retry_idx + 1))
                    else:
                        logger.debug("PASSED PARALLEL ERROR in {}th task:".format(idx) + format_exc(name='mlchain.workflows.parallel'))
            self.update_progress_bar()

    async def dispatch(self):
        """
        When you run parallel inside another parallel, please use this function
        """
        if len(self.tasks) == 0:
            return None 

        outputs = [None] * len(self.tasks)

        async with trio.open_nursery() as nursery:
            for idx, task in enumerate(self.tasks):
                if hasattr(task, 'to_async') and callable(task.to_async):
                    nursery.start_soon(self.__call_async, task.to_async(), outputs, idx, self.limiter, self.max_retries, self.pass_fail_job)
                elif inspect.iscoroutinefunction(task) or (not inspect.isfunction(task) and hasattr(task, '__call__') and inspect.iscoroutinefunction(task.__call__)):
                    nursery.start_soon(self.__call_async, task, outputs, idx, self.limiter, self.max_retries, self.pass_fail_job)
                else:
                    nursery.start_soon(self.__call_sync, task, outputs, idx, self.limiter, self.max_retries, self.pass_fail_job)

        return outputs

    def exec_task(self,task,idx = None):
        for retry_idx in range(self.max_retries):
            try:
                output = task.exec()
                self.update_progress_bar()
                return output
            except Exception as ex:
                if retry_idx == self.max_retries - 1 and not self.pass_fail_job:
                    return ex
                elif retry_idx < self.max_retries - 1 or not self.verbose:
                    logger.error(
                        "PARALLEL ERROR in {0}th task and retry task, run times = {1}".format(idx, retry_idx + 1))
                else:
                    logger.debug("PASSED PARALLEL ERROR in {}th task:".format(idx) + format_exc(
                        name='mlchain.workflows.parallel'))
        return None

    def run(self, progress_bar:bool=False, notebook_mode:bool=False):
        """
        When you run parallel in root, please use this function
        :progress_bar: Use tqdm to show the progress of calling Parallel
        :notebook_mode: Put it to true if run mlchain inside notebook
        """
        if self.threading:
            pool = ThreadPool(max(1,self.max_threads))
            if progress_bar:
                self.show_progress_bar = True
                self.progress_bar = TrioProgress(total=len(self.tasks), notebook_mode=notebook_mode)
            async_result = []
            for idx,task in enumerate(self.tasks):
                async_result.append(pool.apply_async(self.exec_task,args=[task,idx]))
            results = []
            for result in async_result:
                output = result.get()
                if isinstance(output,Exception):
                    pool.terminate()
                    pool.close()
                    raise output
                results.append(output)
            pool.close()
            return results
        if progress_bar:
            self.show_progress_bar = True
            self.progress_bar = TrioProgress(total=len(self.tasks), notebook_mode=notebook_mode)
        return trio.run(self.dispatch)