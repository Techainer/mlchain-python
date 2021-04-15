import logging
import os
import time
import unittest
import threading

from click.testing import CliRunner
from mlchain.cli.main import main
from mlchain.workflows import Background, Task

from .utils import test_breaking_process

logger = logging.getLogger()
cli = main(is_testing=True)
runner = CliRunner()

def launch_test_server():
    test_breaking_process(runner, cli, args = 'run'.split(), new_pwd = 'tests/dummy_server', prog_name = 'python3 -m mlchain', wait_time = 60)

class TestClient(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.is_windows = os.name == 'nt'

    def test_client(self):
        if self.is_windows:
            return 0
        import numpy as np
        from mlchain.client import Client
        server = threading.Thread(target=launch_test_server)
        server.start()
        time.sleep(5)
        logger.info("Assume dummy model are ready. Testing client ...")

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
        server.join()
