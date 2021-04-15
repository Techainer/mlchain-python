import logging
import unittest
from threading import Timer
import os

try:
    import cv2
except Exception:
    # Travis Windows will fail here
    pass


import numpy as np
from mlchain.base import ServeModel
from mlchain.server.flask_server import FlaskServer
from mlchain.server.grpc_server import GrpcServer
from mlchain.server.starlette_server import StarletteServer
from mlchain.decorators import except_serving
from mlchain.base.serve_model import batch,non_thread
from .utils import test_breaking_process_server

logger = logging.getLogger()

class Model():
    """ Just a dummy model """
    def __init__(self):
        logger.info("Init test server sucessfully!")

    def predict(self, image: np.ndarray):
        """
        Resize input to 100 by 100.
        Args:
            image (numpy.ndarray): An input image.
        Returns:
            The image (np.ndarray) at 100 by 100.
        """
        image = cv2.resize(image, (100, 100))
        return image

    @non_thread()
    def predict_non_thread(self, image: np.ndarray):
        image = cv2.resize(image, (100, 100))
        return image

    @batch(name='predicts',variables={'images': np.ndarray},
           default={'batch_size': 5}, variable_names={'images':'image'},
           max_queue=100, max_batch_size=32)
    def predict_batch(self, images: np.ndarray):
        for image in images:
            image = cv2.resize(image, (100, 100))
        return images

    @except_serving
    def dummy(self):
        pass


original_model = Model()

class TestServer(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        self.is_not_windows = os.name != 'nt'

    def test_flask_server_init(self):
        try:
            abc = 1
            model_abc = ServeModel(abc)
        except AssertionError:
            pass

        logger.info("Running flask server init test")
        model = ServeModel(original_model)
        flask_model = FlaskServer(model)
        if self.is_not_windows:
            test_breaking_process_server(flask_model, port=10001, expected_exit_code=1)
    
    def test_starlette_server_init(self):
        logger.info("Running starllete server init test")
        model = ServeModel(original_model)
        starlette_model = StarletteServer(model)
        if self.is_not_windows:
            test_breaking_process_server(starlette_model, port=10002, expected_exit_code=0)

    def test_grpc_server_init(self):
        logger.info("Running grpc server init test")
        model = ServeModel(original_model)
        grpc_model = GrpcServer(model)
        # if self.is_not_windows:
        #     test_breaking_process_server(grpc_model, port=10003)


if __name__ == "__main__":
    unittest.main()
