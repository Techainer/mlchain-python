import logging
import unittest

from mlchain.base.utils import *
logger = logging.getLogger()

class TestUtils(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        logger.info("Running utils test")

    def test_nothing(self):
        pass

if __name__ == '__main__':
    unittest.main()
