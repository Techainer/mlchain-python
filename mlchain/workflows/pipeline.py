from multiprocessing.pool import ThreadPool


class Step:
    def __init__(self, func, max_thread=4):
        self.func = func
        self.max_thread = max_thread


class Pipeline:
    def __init__(self, *steps: Step):
        self.steps = steps

    def __call__(self, args):
        self.pools = []
        for step in self.steps:
            p = ThreadPool(step.max_thread)
            args = p.imap(step.func, args)
            self.pools.append(p)
        result = [arg for arg in args]
        for p in self.pools:
            p.close()
        return result
