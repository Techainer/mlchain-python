import logging
import unittest

from mlchain.base.exceptions import MLChainUnauthorized
logger = logging.getLogger()

class TestExceptions(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        logger.info("Running exception test")

    def test_unauthorized(self):
        exception = MLChainUnauthorized("This error is expected")
        self.assertTrue(exception.status_code == 401)
        try:
            raise exception
        except Exception:
            pass

if __name__ == '__main__':
    unittest.main()
