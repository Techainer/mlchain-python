
import time 
from multiprocessing.pool import ThreadPool
from .task import Task
from collections import deque
import logging
from typing import List
from mlchain.base.log import format_exc

logger = logging.getLogger(__name__)

class Step:
    """
    Step of a Pipeline 
    """
    def __init__(self, func, max_thread:int=1, max_calls:int=None, interval:float=1.0):
        """
        Initialize step with func and max_threads
        :max_thread: Maximum thread parallel of a Step
        :max_calls: Maximum call step in interval, fps = max_calls / interval
        """
        self.func = func
        self.max_thread = max_thread
        self.max_calls = max_calls 
        self.interval = interval
        self.index = None
        self.thread_pool = ThreadPool(max(1, self.max_thread))

        if max_calls is not None: 
            self.interval_time = self.period / self.max_calls

        self.accept_next_call = time.time()

    def __call__(self, input): 
        if self.max_calls is not None: 
            if time.time() < self.accept_next_call:
                time.sleep(self.interval_time)
            self.accept_next_call = time.time() + self.interval_time

        return self.func(input)

class StepOutput: 
    """
    Output of Step Task
    """
    def __init__(self, input, steps: List, fail_step_list:List, pass_fail_job:bool=False): 
        """
        :input: Input of the first step
        :steps: list of Step
        :fail_step_list: The list of failed Step
        :pass_fail_job: Ignore fail step or not 
        """
        self.last_step_output = input
        self.steps = steps
        self.n_steps = len(steps)
        self.current_step = -1
        self.pass_fail_job = pass_fail_job
        self.fail_step_list = fail_step_list

        self.is_success = False
        self.exception = None

        self.output = []

        self.next_step()

    def exec_task(self, task: Task): 
        try:
            output = task.exec()
        except Exception as ex:
            self.exception = ex
            self.fail_step_list.append(self)

            if not self.pass_fail_job:
                logger.error(
                        f"PIPELINE ERROR in {self.current_step}th step: {format_exc()}"
                    )
        
        if self.exception is None:
            self.output.append(output)
            self.last_step_output = output
            self.next_step()
        
    def next_step(self): 
        self.current_step += 1
        if self.current_step >= self.n_steps:
            self.is_success = True
            return self.output
        
        current_step = self.steps[self.current_step]
        task = Task(current_step, self.last_step_output)
        current_step.thread_pool.apply_async(self.exec_task, args=[task])  

    @property
    def is_done(self): 
        return self.current_step >= self.n_steps and self.is_success and self.exception is None
    
    @property
    def is_fail(self): 
        return self.exception is not None

class Pipeline(object): 
    def __init__(self, *steps: Step): 
        """
        Pipeline multiple steps 
        """
        if len(steps) == 0:
            raise ValueError('Input Pipeline should have at least one Step!')

        self.steps = steps
        self.n_steps = len(self.steps)

        # When the pipeline is running loop forever, this is the way to stop it 
        self.running = False

    def stop(self): 
        """ Stop a Pipeline """
        self.running = False 

    def run(self, inputs, max_processing_queue:int=1000, return_output:bool=True, loop_forever:bool=False, pass_fail_job:bool=False, progress_bar=True): 
        def _process_first_task_done():
            the_output = self.processing_queue.popleft()
            check_having_update = True

            if return_output: 
                self.output_queue.append(the_output)
            else: 
                del the_output
            return check_having_update

        """
        :inputs: A list or an iterator 
        :max_processing_queue: Max of queue for processing task 
        :return_output: Return output or not 
        :loop_forever: Loop forever or not, for infinite inputs
        :pass_fail_job: Only logging the failure job, not stop Pipeline
        :progress_bar: Use tqdm to show the progress of calling Pipeline 
        """
        inputs = iter(inputs)
        
        self.running = True 
        self.processing_queue = deque()
        self.output_queue = []
        self.progress_bar = progress_bar
        self.fail_step_list = []

        for idx, step in enumerate(self.steps):
            step.index = idx

        while self.running: 
            check_having_update = False
            # Pop done processing and add into self.output_queue
            while len(self.processing_queue) > 0 and self.processing_queue[0].is_done: 
                check_having_update = _process_first_task_done()

            # Processing more inputs 
            while self.running and len(self.processing_queue) < max_processing_queue:
                try:
                    input = next(inputs)
                except StopIteration:
                    logger.info("Processing pipeline waiting because there's no input left")
                    if not loop_forever:
                        logger.info("Processing pipeline stop because there's no input left, if you want to loop forever, use loop_forever")
                        self.stop()
                    break 
            
                check_having_update = True
                the_step_output = StepOutput(input=input, steps = self.steps, fail_step_list=self.fail_step_list, pass_fail_job=pass_fail_job)
                self.processing_queue.append(the_step_output)

            # Check is any step fail
            if len(self.fail_step_list) > 0:
                if not pass_fail_job: 
                    self.stop()
                    logger.error("Pipeline error, stop now!")
                    raise self.fail_step_list[0].exception

            if not check_having_update: 
                logger.debug("There's no done task update")
                time.sleep(0.01)

        # Check already run all then return 
        while len(self.processing_queue) > 0:
            if self.processing_queue[0].is_done:
                check_having_update = _process_first_task_done()
            elif self.processing_queue[0].is_fail:
                if not pass_fail_job:
                    self.stop()
                    logger.error("Pipeline error, stop now!")
                    raise self.fail_step_list[0].exception
                else:
                    self.processing_queue.popleft()
            else: 
                time.sleep(0.01)

        for step in self.steps:
            step.thread_pool.close()

        logger.info("Stopped Pipeline")
        return self.output_queue
        