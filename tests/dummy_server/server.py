import logging

import cv2
import numpy as np
from mlchain.base import ServeModel
from mlchain.decorators import except_serving

logger = logging.getLogger()


class Model():
    """ Just a dummy model """
    def __init__(self):
        logger.info("Init dummy model sucessfully!")


    def predict(self, image: np.ndarray = None):
        """
        Resize input to 100 by 100.
        Args:
            image (numpy.ndarray): An input image.
        Returns:
            The image (np.ndarray) at 100 by 100.
        """
        if image is None:
            return 'Hihi'
        image = cv2.resize(image, (100, 100))
        return image

    @except_serving
    def dummy(self):
        pass

    def get_error(self):
        raise Exception("This exception is expected")


# Define model
model = Model()

# Serve model
serve_model = ServeModel(model)

# Deploy model
if __name__ == '__main__':
    from mlchain.server import FlaskServer

    # Run flask model with upto 12 threads
    FlaskServer(serve_model).run(port=5000, threads=12)
