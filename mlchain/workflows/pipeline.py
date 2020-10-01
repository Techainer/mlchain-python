
import time 
from .background import Background
from .task import Task, SyncTask
from collections import deque
import threading
import logging

class Step:
    """
    Step of a Pipeline 
    """
    def __init__(self, func, max_thread:int=1, max_calls:int=None, interval:float=1.0):
        """
        Initialize step with func and max_threads
        :max_calls: Maximum call step in interval, fps = max_calls / interval
        """
        self.func = func
        self.max_thread = max_thread
        self.max_calls = max_calls 
        self.interval = interval
        
        if max_calls is not None: 
            self.interval_time = self.period / self.max_calls

        self.accept_next_call = time.time()

    def __call__(self, input): 
        if self.max_calls is not None: 
            self.accept_next_call = time.time() + self.interval_time

        return self.func(input)

    @property
    def can_call(self): 
        return time.time() > self.accept_next_call

class StepOutput: 
    def __init__(self, steps, step_max_thread_dict, pass_fail_job:bool=False): 
        self.steps = steps
        self.current_step = 0
        self.is_available = True 
        self.max_step_index = len(steps)
        self.step_max_thread_dict = step_max_thread_dict
        self.pass_fail_job = pass_fail_job
        self.is_fail = False

        self.output = []

    def increase_current_step(self, callback=None): 
        self.step_max_thread_dict[self.current_step] += 1
        self.current_step += 1
        self.is_available = True 

        if isinstance(self.output[-1].output, tuple) and len(self.output[-1].output) == 2 and self.output[-1].output[0] == "MLCHAIN_BACKGROUND_ERROR": 
            self.is_fail = True
            self.current_step = self.max_step_index
            self.is_done = True 
            
            if not self.pass_fail_job: 
                raise Exception("Mlchain Pipeline error, stop here!")

        if callback:
            t = threading.Thread(target=callback)
            t.daemon = True
            t.start()

        # Call next step 
        if self.need_call:
            self.call_next_step()
        
    def call_first_step(self, input, callback=None): 
        self.is_available = False
        self.step_max_thread_dict[self.current_step] -= 1 

        if not self.is_done:
            self.output.append(Background(Task(self.steps[self.current_step], input), callback=SyncTask(self.increase_current_step, callback)).run(pass_fail_job=self.pass_fail_job))

    def call_next_step(self, callback=None): 
        self.is_available = False
        self.step_max_thread_dict[self.current_step] -= 1 
      
        self.output.append(Background(Task(self.steps[self.current_step], self.output[-1].output), callback=SyncTask(self.increase_current_step, callback)).run(pass_fail_job=self.pass_fail_job))

    @property
    def is_done(self): 
        return self.current_step >= self.max_step_index

    @property
    def need_call(self): 
        if self.is_done:
            return False
        return self.is_available and self.step_max_thread_dict[self.current_step] > 0 

class Pipeline(object): 
    def __init__(self, *steps: Step): 
        """
        Pipeline multiple steps 
        """
        if len(steps) == 0:
            raise ValueError('Input Pipeline should have at least one Step!')

        self.steps = steps
        self.max_step_index = len(self.steps)

        # When the pipeline is running loop forever, this is the way to stop it 
        self.running = False

    def stop(self): 
        """ Stop a Pipeline """
        self.running = False 

    def run(self, inputs, max_processing_queue:int=1000, return_output:bool=True, loop_forever:bool=False, pass_fail_job:bool=False): 
        """
        :inputs: A list or an iterator 
        :max_processing_queue: Max of queue for processing task 
        :return_output: Return output or not 
        :loop_forever: Loop forever or not, for infinite inputs
        :pass_fail_job: Only logging the failure job, not stop pipeline 
        """
        inputs = iter(inputs)
        
        self.running = True 
        self.processing_queue = deque()
        self.output_queue = []
        self.step_max_thread_dict = {idx:step.max_thread for idx, step in enumerate(self.steps)}

        while True and self.running: 
            check_having_update = False
            # Pop done processing and add into self.output_queue
            while len(self.processing_queue) > 0 and self.processing_queue[0].is_done: 
                the_output = self.processing_queue.popleft()
                if the_output.is_fail and not pass_fail_job: 
                    self.stop()
                    raise Exception("Pipeline error, stop now!")

                check_having_update = True

                if return_output: 
                    if not the_output.is_fail:
                        self.output_queue.append(the_output)
                else: 
                    del the_output

            # Processing more inputs 
            while True and self.step_max_thread_dict[0] > 0 and len(self.processing_queue) < max_processing_queue:
                try:
                    input = next(inputs)
                except StopIteration:
                    logging.info("Processing pipeline waiting because there's no input left")
                    if not loop_forever:
                        logging.info("Processing pipeline stop because there's no input left, if you want to loop forever, use loop_forever")
                        self.stop()
                    break 
            
                check_having_update = True
                the_step_output = StepOutput(steps = self.steps, step_max_thread_dict=self.step_max_thread_dict, pass_fail_job=pass_fail_job)
                the_step_output.call_first_step(input)
                
                self.processing_queue.append(the_step_output)

            # Processing processing steps to next step
            for processing_step in self.processing_queue: 
                if processing_step.is_fail and not pass_fail_job: 
                    self.stop()
                    raise Exception("Pipeline error, stop now!")

            if not check_having_update: 
                logging.debug("There's no done task update")
                time.sleep(0.01)

        # Check already run all then return 
        while len(self.processing_queue) > 0:
            if self.processing_queue[0].is_done:
                the_output = self.processing_queue.popleft()

                if the_output.is_fail and not pass_fail_job: 
                    self.stop()
                    raise Exception("Pipeline error, stop now!")

                if return_output and len(the_output.output) == self.max_step_index: 
                    if not the_output.is_fail:
                        self.output_queue.append(the_output)
                else: 
                    del the_output
            else: 
                time.sleep(0.01)

        logging.info("Stopped Pipeline")
        return self.output_queue