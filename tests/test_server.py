import logging
import unittest
from threading import Timer
import os

import cv2
import numpy as np
from mlchain.base import ServeModel
from mlchain.server.flask_server import FlaskServer
from mlchain.server.grpc_server import GrpcServer
from mlchain.server.quart_server import QuartServer
from mlchain.decorators import except_serving

logger = logging.getLogger()

class Model():
    """ Just a dummy model """

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
    
    @except_serving
    def dummy(self):
        pass

original_model = Model()

def test_breaking_process(runner, port, wait_time=10):
    from multiprocessing import Process
    from threading import Timer
    from os import kill, getpid
    from signal import SIGINT

    def background():
        Timer(wait_time, lambda: kill(getpid(), SIGINT)).start()
        runner.run(port=port, thread=1)

    p = Process(target=background)
    p.start()


class TestServer(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)

    def test_flask_server_init(self):
        logger.info("Running flask server init test")
        model = ServeModel(original_model)
        flask_model = FlaskServer(model)
        test_breaking_process(flask_model, port=10001)
    
    def test_quart_server_init(self):
        logger.info("Running quart server init test")
        model = ServeModel(original_model)
        quart_model = QuartServer(model)
        # test_breaking_process(quart_model, port=10002)

    def test_grpc_server_init(self):
        logger.info("Running grpc server init test")
        model = ServeModel(original_model)
        grpc_model = GrpcServer(model)
        # test_breaking_process(grpc_model, port=10003)


if __name__ == "__main__":
    unittest.main()