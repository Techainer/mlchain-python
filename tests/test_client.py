import logging
import unittest
import time
import os

from click.testing import CliRunner
from mlchain.cli.main import main
from mlchain.workflows import Background, Task

logger = logging.getLogger()
cli = main(is_testing=True)
runner = CliRunner()

def test_breaking_process(runner, cli, args, new_pwd, prog_name, wait_time=10):
    from multiprocessing import Queue, Process
    from threading import Timer
    from time import sleep
    from os import kill, getpid
    from signal import SIGINT

    q = Queue()

    # Running out app in SubProcess and after a while using signal sending 
    # SIGINT, results passed back via channel/queue  
    def background():
        Timer(wait_time, lambda: kill(getpid(), SIGINT)).start()
        os.chdir(new_pwd)
        result = runner.invoke(cli, args, prog_name=prog_name)
        q.put(('exit_code', result.exit_code))
        q.put(('output', result.output))

    p = Process(target=background)
    p.start()

    results = {}

    while p.is_alive():
        sleep(0.5)
    else:
        while not q.empty():
            key, value = q.get()
            results[key] = value
    logger.info('Output of `mlchain run`:\n' + results['output'])
    assert results['exit_code'] == 0


class TestClient(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)

    def test_client(self):
        import numpy as np
        from mlchain.client import Client
        task = Task(test_breaking_process, runner, cli, args='run'.split(), new_pwd='tests/dummy_server', prog_name='python -m mlchain')
        background = Background(task=task).run()
        time.sleep(3)

        # Test normal client
        model = Client(api_address='http://localhost:12345').model(check_status=True)
        input_image = np.ones((200, 200), dtype=np.uint8)
        result_image = model.predict(input_image)
        assert result_image.shape == (100, 100)

        # Test client with exception
        try:
            model.predict('abc')
            logger.info('This is supose to fail')
        except Exception:
            pass

        # Test Swagger UI
        import requests
        requests.get('http://localhost:12345', timeout=5)
        requests.get('http://localhost:12345/swagger/', timeout=5)