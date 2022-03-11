import os
from multiprocessing.pool import ThreadPool
from mlchain.base.log import format_exc, except_handler, logger
from typing import List 

class TrioProgress:
    def __init__(self, total, notebook_mode=False, **kwargs):
        if notebook_mode:  # pragma: no cover
            from tqdm.notebook import tqdm
        else:
            from tqdm import tqdm

        self.tqdm = tqdm(total=total, **kwargs)
        self.count = 0
        self.total = total

    def task_processed(self):
        self.tqdm.update(1)
        self.count += 1
        if self.count == self.total: 
            self.tqdm.close()

class Parallel:
    """
    Build a collection of tasks to be executed in parallel
    :tasks: List of [Task, function] items
    :max_threads: Maximum Threads for this Parallel 
    :max_retries: Maximum retry time when a task fail 
    :pass_fail_job: Pass or Raise error when a task run fail 
    :verbose: Print error or not 
    """

    def __init__(
        self,
        tasks: List,
        max_threads: int = 10,
        max_retries: int = 0,
        pass_fail_job: bool = False,
        verbose: bool = True,
    ):
        """
        :tasks: [Task, function] items
        :max_threads: Maximum threads to Parallel, max_threads=0 means no limitation 
        :max_retries: How many time retry when job fail
        :pass_fail_job: No exeption when a job fail 
        :verbose: Verbose or not 
        """

        assert isinstance(tasks, list) and all(
            callable(task) for task in tasks
        ), "You have to transfer a list of callable instances or mlchain.Task"
        self.tasks = tasks
        if max_threads == -1:
            max_threads = 100
        elif max_threads == 0:
            max_threads = os.cpu_count()
        self.max_threads = max(0, max_threads)

        self.max_retries = max(max_retries + 1, 1)
        self.pass_fail_job = pass_fail_job
        self.verbose = verbose
        self.show_progress_bar = False
        self.progress_bar = None

    def update_progress_bar(self):
        if self.show_progress_bar:
            self.progress_bar.task_processed()

    def exec_task(self, task, idx=None):
        for retry_idx in range(self.max_retries):
            try:
                output = task.exec()
                self.update_progress_bar()
                return output
            except Exception as ex:
                if retry_idx == self.max_retries - 1 and not self.pass_fail_job:
                    return ex
                if retry_idx < self.max_retries - 1 or not self.verbose:
                    logger.error(
                        "PARALLEL ERROR in {0}th task and retry task, "
                        "run times = {1}".format(idx, retry_idx + 1)
                    )
                else:
                    logger.debug(
                        "PASSED PARALLEL ERROR in {}th task:".format(idx, format_exc(name="mlchain.workflows.parallel"))
                    )
        return None

    def run(self, progress_bar: bool = False, notebook_mode: bool = False):
        """
        When you run parallel in root, please use this function
        :progress_bar: Use tqdm to show the progress of calling Parallel
        :notebook_mode: Put it to true if run mlchain inside notebook
        """
        pool = ThreadPool(max(1, self.max_threads))
        if progress_bar:
            self.show_progress_bar = True
            self.progress_bar = TrioProgress(
                total=len(self.tasks), notebook_mode=notebook_mode
            )

        async_result = [
            pool.apply_async(self.exec_task, args=[task, idx])
            for idx, task in enumerate(self.tasks)
        ]

        results = []
        for result in async_result:
            output = result.get()
            if isinstance(output, Exception):
                pool.terminate()
                pool.close()
                raise output
            results.append(output)
        pool.close()
        return results
