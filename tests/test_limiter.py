import logging
import unittest
import time

from mlchain.workflows import RateLimiter
logger = logging.getLogger()

@RateLimiter(max_calls=3, period=1)
def do_nothing(i):
    return i

class TestLimiter(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        logger.info("Running limiter test")

    def test_limiter(self):
        start_time = time.time()
        limiter = RateLimiter(max_calls=3, period=1)
        for i in range(10):
            with limiter:
                pass
        total_time = time.time() - start_time
        assert total_time >= 3

    def test_limiter_2(self):
        start_time = time.time()
        for i in range(10):
            do_nothing(i)
        total_time = time.time() - start_time
        assert total_time >= 3

    def test_limiter_fail(self):
        try:
            limiter = RateLimiter(max_calls=1, period=0)
        except ValueError:
            pass

        try:
            limiter = RateLimiter(max_calls=0, period=1)
        except ValueError:
            pass

    def test_limiter_with_callback(self):
        start_time = time.time()
        global abc
        abc = 0
        def callback(i):
            global abc
            abc += 1
        limiter = RateLimiter(max_calls=3, period=1, callback=callback)
        for i in range(10):
            with limiter:
                pass
        total_time = time.time() - start_time
        assert total_time >= 3

if __name__ == '__main__':
    unittest.main()
