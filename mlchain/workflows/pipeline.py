from multiprocessing.pool import ThreadPool


class Step:
    def __init__(self, func, max_thread=4):
        self.func = func
        self.max_thread = max_thread

    def __call__(self, args):
        pool = ThreadPool(self.max_thread)
        res = pool.imap(self.func, args)
        res = [r for r in res]
        pool.close()
        return res


class Pipeline:
    def __init__(self, *steps: Step):
        self.steps = steps

    def __call__(self, args):
        pools = []
        for step in self.steps:
            pool = ThreadPool(step.max_thread)
            args = pool.imap(step.func, args)
            pools.append(pool)
        result = [arg for arg in args]
        for pool in pools:
            pool.close()
        return result
