import logging
import re
import unittest
import os
import time

from mlchain.workflows import Parallel, Task, Background, Pipeline, Step

logger = logging.getLogger()

class TestWorkflow(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)

    def test_mlchain_parallel(self):
        input_list = [1, 2, 3, 4, 5]
        def dummy_task(i):
            time.sleep(0.1)
            return i + 1

        tasks = [Task(dummy_task, i) for i in input_list]
        _ = Parallel(tasks, max_threads=0).run()
        _ = Parallel(tasks, max_threads=-1).run()
        _ = Parallel([]).run()
        _ = Parallel([], threading=False).run()
        output = Parallel(tasks, max_threads=2).run(progress_bar=True)
        logger.info(output)
        assert output == [2, 3, 4, 5, 6]

        output = Parallel(tasks, max_threads=2, threading=False).run(progress_bar=True)
        logger.info(output)
        assert output == [2, 3, 4, 5, 6]

    def test_mlchain_parallel_pass_fail_job(self):
        input_list = [1, 2, 3, 4, 5]
        def dummy_task(i):
            time.sleep(0.1)
            if i == 3:
                raise Exception('Job failed')
            return i + 1

        tasks = [Task(dummy_task, i) for i in input_list]
        output = Parallel(tasks, max_threads=2, pass_fail_job=True, max_retries=2).run(progress_bar=True)
        logger.info(output)
        assert output == [2, 3, None, 5, 6]

        output = Parallel(tasks, max_threads=2, pass_fail_job=True, threading=False, max_retries=2).run(progress_bar=True)
        logger.info(output)
        assert output == [2, 3, None, 5, 6]

        try:
            output = Parallel(tasks, max_threads=2, threading=False).run(progress_bar=True)
            raise AssertionError("This is supose to fail")
        except Exception:
            pass

        try:
            output = Parallel(tasks, max_threads=2).run(progress_bar=True)
            raise AssertionError("This is supose to fail")
        except Exception:
            pass

    def test_mlchain_parallel_in_parallel(self):
        input_list = [1, 2, 3, 4, 5]
        def dummy_task(i):
            def sub_task(j):
                return j + 2
            all_sub_task = [Task(sub_task, j) for j in range(i)]
            sub_output = Parallel(all_sub_task, max_threads=2).run()
            return sum(sub_output)

        tasks = [Task(dummy_task, i) for i in input_list]
        output = Parallel(tasks, max_threads=2, threading=False).run(progress_bar=True)
        logger.info(output)
        assert output == [2, 5, 9, 14, 20]

    def test_mlchain_background(self):
        x = []
        def dummy_task(n):
            for i in range(n):
                x.append(i)
        task = Task(dummy_task, 10)
        background = Background(task).run()
        time.sleep(1)
        logger.info(x)
        assert x == list(range(10))
        background.stop()

        background = Background(task, interval=0.1).run()
        time.sleep(1)
        logger.info(x)
        assert x[:10] == list(range(10))
        assert len(x) > 10
        background.stop()

    def test_mlchain_background_pass_fail_job(self):
        x = []
        def dummy_task():
            raise Exception('This exception is expected')
        task = Task(dummy_task)

        background = Background(task, interval=0.01).run(pass_fail_job=True)
        time.sleep(0.02)
        logger.info(x)
        background.stop()

    def test_mlchain_async_task(self):
        async def dummy_task(n):
            return n+1
        task = Task(dummy_task, 5)

    def test_mlchain_pipeline(self):
        def step_1(i):
            time.sleep(0.001)
            return i * 2

        def step_2(i):
            time.sleep(0.001)
            return i * 2

        def step_3(i):
            time.sleep(0.001)
            return i + 1

        pipeline = Pipeline(
            Step(step_1, max_thread = 1),
            Step(step_2, max_thread = 1),
            Step(step_3, max_thread = 1)
        )
        inputs = range(20)
        results = pipeline.run(inputs)
        assert [x.output[-1].output for x in results] == [1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61, 65, 69, 73, 77]