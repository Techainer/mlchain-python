# -*- coding: utf-8 -*-
""" 
Async support for 3.5+ 
This code is inspired by: https://github.com/RazerM/ratelimiter
"""
import time
import asyncio
import functools
import threading

class RateLimiter(object):
    """Provides rate limiting for an operation with a configurable number of
    requests for a time period.
    """

    def __init__(self, max_calls:int, period:float=1.0, callback=None):
        """Initialize a RateLimiter object which enforces as much as max_calls
        operations on period (eventually floating) number of seconds.
        """
        if period <= 0:
            raise ValueError('Rate limiting period should be > 0')
        if max_calls <= 0:
            raise ValueError('Rate limiting number of calls should be > 0')

        # We're using a deque to store the last execution timestamps, not for
        # its maxlen attribute, but to allow constant time front removal.
        self.average_call_time = 0 

        self.period = period
        self.max_calls = max_calls
        self.callback = callback
        self.interval_time = self.period / self.max_calls

        self._lock = threading.Lock()
        self._alock = None
        self.call_times = 0 

        self.last_time = time.time()-self.interval_time
        self.average_call_time = 0 
        # Lock to protect creation of self._alock
        self._init_lock = threading.Lock()

    def __call__(self, f):
        """The __call__ function allows the RateLimiter object to be used as a
        regular function decorator.
        """
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            with self:
                return f(*args, **kwargs)
        return wrapped

    def __enter__(self):
        with self._lock:
            expect_call_time = self.last_time + self.interval_time - self.average_call_time
            if expect_call_time >= time.time():
                if self.callback:
                    t = threading.Thread(target=self.callback, args=(expect_call_time,))
                    t.daemon = True
                    t.start()
                sleeptime = expect_call_time - time.time()
                if sleeptime > 0:
                    time.sleep(sleeptime)
            
            self.start_function = time.time()
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.call_times <= 3: 
            self.average_call_time  = time.time() - self.start_function
        else: 
            self.average_call_time = (time.time() - self.start_function + self.average_call_time * 2)/3

        self.call_times += 1 
        self.last_time = time.time()

class AsyncRateLimiter(RateLimiter):
    def _init_async_lock(self):
        with self._init_lock:
            if self._alock is None:
                self._alock = asyncio.Lock()

    async def __aenter__(self):
        if self._alock is None:
            self._init_async_lock()

        async with self._alock:
            expect_call_time = self.last_time + self.interval_time - self.average_call_time
            if expect_call_time >= time.time():
                if self.callback:
                    asyncio.ensure_future(self.callback(until))

                sleeptime = expect_call_time - time.time()
                if sleeptime > 0:
                    await asyncio.sleep(sleeptime)
            
            self.start_function = time.time()
            return self

    async def __aexit__(self, exc_type, exc_value, traceback):
         return super(AsyncRateLimiter, self).__exit__(exc_type, exc_value, traceback)