try:
    from gunicorn.app.base import BaseApplication
except Exception as ex:
    import warnings

    warnings.warn("Import error {0}".format(ex))


    class BaseApplication(object):
        def __init__(self):
            raise ImportError("Can't import gunicorn. Please set gunicorn = False")


class GunicornWrapper(BaseApplication):
    def __init__(self, app, **kwargs):
        self.application = app
        self.options = kwargs
        super(GunicornWrapper, self).__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

        from mlchain.base.gunicorn_config import on_starting
        self.cfg.set("on_starting", on_starting)

    def load(self):
        return self.application


class HypercornWrapper:
    def __init__(self, app, **kwargs):
        self.application = app
        self.worker_class = kwargs.pop('worker_class', 'asyncio')
        self.options = kwargs

        from hypercorn.config import Config
        self.config = Config().from_mapping(kwargs)

    def run(self):
        from hypercorn.asyncio import serve
        import asyncio

        if 'uvloop' in self.worker_class:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            loop.run_until_complete(serve(self.application, self.config))
        else:
            import sys
            if sys.version_info.major == 3 and sys.version_info.minor <= 6:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(serve(self.application, self.config))
            else:
                asyncio.run(serve(self.application, self.config))
