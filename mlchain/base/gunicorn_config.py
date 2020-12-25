from mlchain.config import init_sentry

def on_starting(server): 
    init_sentry()