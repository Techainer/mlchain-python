from mlchain.config import init_sentry

def post_worker_init(worker):
    init_sentry()