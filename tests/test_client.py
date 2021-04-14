import logging
import unittest
import time
import os

from click.testing import CliRunner
from mlchain.cli.main import main
from mlchain.workflows import Background, Task
from .utils import test_breaking_process

logger = logging.getLogger()
cli = main(is_testing=True)
runner = CliRunner()



class TestClient(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.is_windows = os.name == 'nt'

    def test_client(self):
        if self.is_windows:
            return 0
        import numpy as np
        from mlchain.client import Client
        task = Task(test_breaking_process, runner, cli, args='run'.split(), new_pwd='tests/dummy_server', prog_name='python3 -m mlchain')
        background = Background(task=task).run()
        time.sleep(3)

        # Test normal client
        model = Client(api_address='http://localhost:12345', serializer='json').model(check_status=True)
        input_image = np.ones((200, 200), dtype=np.uint8)
        result_image = model.predict(input_image)
        assert result_image.shape == (100, 100)

        model = Client(api_address='http://localhost:12345', serializer='msgpack').model(check_status=True)
        result_image_2 = model.predict(input_image)
        assert result_image_2.shape == (100, 100)

        model = Client(api_address='http://localhost:12345', serializer='msgpack_blosc').model(check_status=True)
        result_image_3 = model.predict(input_image)
        assert result_image_3.shape == (100, 100)

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
