import os
import click
import importlib
import sys
import GPUtil
from mlchain import logger
from mlchain.server import MLServer
from mlchain.base import ServeModel
from mlchain.server.authentication import Authentication


def select_gpu():
    try:
        gpus = GPUtil.getFirstAvailable()
    except:
        gpus = []
    if len(gpus) == 0:
        gpus = [0]
    while True:
        for gpu in gpus:
            yield str(gpu)


def prepare_import(path):
    """Given a filename this will try to calculate the python path, add it
    to the search path and return the actual module name that is expected.
    """
    path = os.path.realpath(path)

    fname, ext = os.path.splitext(path)
    if ext == ".py":
        path = fname

    if os.path.basename(path) == "__init__":
        path = os.path.dirname(path)

    module_name = []

    # move up until outside package structure (no __init__.py)
    while True:
        path, name = os.path.split(path)
        module_name.append(name)

        if not os.path.exists(os.path.join(path, "__init__.py")):
            break

    if sys.path[0] != path:
        sys.path.insert(0, path)

    return ".".join(module_name[::-1])


def get_env(_k):
    return 'GUNICORN_' + _k.upper()


op_config = click.option("--config", "-c", default=None, help="file json or yaml")
op_name = click.option("--name", "-n", default=None, help="name service")
op_host = click.option("--host", "-h", default=None, help="The interface to bind to.")
op_port = click.option("--port", "-p", default=None, help="The port to bind to.")
op_bind = click.option("--bind", "-b", required=False, multiple=True)
op_wrapper = click.option('--wrapper', 'wrapper', flag_value=None,
                          default=True)
op_gunicorn = click.option('--gunicorn', 'wrapper', flag_value='gunicorn')
op_hypercorn = click.option('--hypercorn', 'wrapper', flag_value='hypercorn')
op_flask = click.option('--flask', 'server', flag_value='flask')
op_quart = click.option('--quart', 'server', flag_value='quart')
op_grpc = click.option('--grpc', 'server', flag_value='grpc')
op_worker = click.option('--workers', '-w', 'workers', default=None, type=int)
op_mode = click.option('--mode', '-m', 'mode', default=None, type=str)
op_api_format = click.option('--api_format', '-a', 'api_format', default=None, type=str)


@click.command("run", short_help="Run a development server.", context_settings={"ignore_unknown_options": True})
@click.argument('entry_file', nargs=1, required=False, default=None)
@op_host
@op_port
@op_bind
@op_gunicorn
@op_hypercorn
@op_flask
@op_quart
@op_grpc
@op_worker
@op_config
@op_name
@op_mode
@op_api_format
@click.option('--ngrok/--no-ngrok', default=False, type=bool)
@click.argument('kws', nargs=-1)
def run_command(entry_file, host, port, bind, wrapper, server, workers, config,
                name, mode, api_format, ngrok, kws):
    kws = list(kws)
    if isinstance(entry_file, str) and not os.path.exists(entry_file):
        kws = [entry_file] + kws
        entry_file = None
    from mlchain import config as mlconfig
    default_config = False
    if config is None:
        default_config = True
        config = 'mlconfig.yaml'

    if os.path.isfile(config):
        config = mlconfig.load_file(config)
        if config is None:
            raise AssertionError("Not support file config {0}".format(config))
    else:
        if not default_config:
            raise FileNotFoundError("Not found file {0}".format(config))
        config = {}
    if 'mode' in config and 'env' in config['mode']:
        if mode in config['mode']['env']:
            config['mode']['default'] = mode
    mlconfig.load_config(config)
    for kw in kws:
        if kw.startswith('--'):
            tokens = kw[2:].split('=', 1)
            if len(tokens) == 2:
                key, value = tokens
                mlconfig.mlconfig.update({key: value})
            else:
                raise AssertionError("Unexpected param {0}".format(kw))
        else:
            raise AssertionError("Unexpected param {0}".format(kw))
    model_id = mlconfig.get_value(None, config, 'model_id', None)
    entry_file = mlconfig.get_value(entry_file, config, 'entry_file', 'server.py')
    host = mlconfig.get_value(host, config, 'host', 'localhost')
    port = mlconfig.get_value(port, config, 'port', 5000)
    server = mlconfig.get_value(server, config, 'server', 'flask')
    if len(bind) == 0:
        bind = None
    bind = mlconfig.get_value(bind, config, 'bind', [])
    wrapper = mlconfig.get_value(wrapper, config, 'wrapper', None)
    if wrapper == 'gunicorn' and os.name == 'nt':
        logger.warning('Gunicorn warper are not supported on Windows. Switching to None instead.')
        wrapper = None
    workers = mlconfig.get_value(workers, config['gunicorn'], 'workers', None)
    if workers is None and 'hypercorn' in config.keys():
        workers = mlconfig.get_value(workers, config['hypercorn'], 'workers', None)
    workers = int(workers) if workers is not None else 1
    name = mlconfig.get_value(name, config, 'name', None)
    cors = mlconfig.get_value(None, config, 'cors', False)

    static_folder = mlconfig.get_value(None, config, 'static_folder', None)
    static_url_path = mlconfig.get_value(None, config, 'static_url_path', None)
    template_folder = mlconfig.get_value(None, config, 'template_folder', None)

    version = mlconfig.get_value(None, config, 'version', '0.0')
    version = str(version)
    api_format = mlconfig.get_value(api_format, config, 'api_format', None)
    api_keys = os.getenv('API_KEYS', None)
    if api_keys is not None:
        api_keys = api_keys.split(';')
    api_keys = mlconfig.get_value(api_keys, config, 'api_keys', None)
    if api_keys is None:
        authentication = None
    else:
        authentication = Authentication(api_keys)
    import logging
    logging.root = logging.getLogger(name)
    logger.debug(dict(
        entry_file=entry_file,
        host=host,
        port=port,
        bind=bind,
        wrapper=wrapper,
        server=server,
        workers=workers,
        name=name,
        mode=mode,
        api_format=api_format,
        kws=kws
    ))
    bind = list(bind)
    if ngrok:
        from pyngrok import ngrok as pyngrok
        endpoint = pyngrok.connect(port=port)
        logger.info("Ngrok url: {0}".format(endpoint))
        os.environ['NGROK_URL'] = endpoint
    if server == 'grpc':
        from mlchain.server.grpc_server import GrpcServer
        app = get_model(entry_file, serve_model=True)
        app = GrpcServer(app, name=name)
        app.run(host, port)
    elif wrapper == 'gunicorn':
        from gunicorn.app.base import BaseApplication
        gpus = select_gpu()

        class GunicornWrapper(BaseApplication):
            def __init__(self, server_, **kwargs):
                assert server_.lower() in ['quart', 'flask']
                self.server = server_.lower()
                self.options = kwargs
                self.autofrontend = False
                super(GunicornWrapper, self).__init__()

            def load_config(self):
                config = {key: value for key, value in self.options.items()
                          if key in self.cfg.settings and value is not None}
                for key, value in config.items():
                    self.cfg.set(key.lower(), value)

                from mlchain.base.gunicorn_config import on_starting
                self.cfg.set("on_starting", on_starting)

            def load(self):
                original_cuda_variable = os.environ.get('CUDA_VISIBLE_DEVICES')
                if original_cuda_variable is None:
                    os.environ['CUDA_VISIBLE_DEVICES'] = str(next(gpus))
                else:
                    logger.info(f"Skipping automatic GPU selection for gunicorn worker since CUDA_VISIBLE_DEVICES environment variable is already set to {original_cuda_variable}")
                serve_model = get_model(entry_file, serve_model=True)
                if isinstance(serve_model, ServeModel):
                    if (not self.autofrontend) and model_id is not None:
                        from mlchain.server.autofrontend import register_autofrontend
                        register_autofrontend(model_id, serve_model=serve_model,
                                              version=version,
                                              endpoint=os.getenv('NGROK_URL'))
                        self.autofrontend = True

                    if self.server == 'flask':
                        from mlchain.server.flask_server import FlaskServer
                        app = FlaskServer(serve_model, name=name, api_format=api_format,
                                          version=version,
                                          authentication=authentication,
                                          static_url_path=static_url_path,
                                          static_folder=static_folder,
                                          template_folder=template_folder)
                        app.register_swagger()
                        if cors:
                            from flask_cors import CORS
                            CORS(app.app)
                        return app.app
                    if self.server == 'quart':
                        from mlchain.server.quart_server import QuartServer
                        app = QuartServer(serve_model, name=name, api_format=api_format,
                                          version=version,
                                          authentication=authentication,
                                          static_url_path=static_url_path,
                                          static_folder=static_folder,
                                          template_folder=template_folder)
                        app.register_swagger()
                        if cors:
                            from quart_cors import cors as CORS
                            CORS(app.app)
                        return app.app
                return None

        if host is not None and port is not None:
            bind.append('{0}:{1}'.format(host, port))

        bind = list(set(bind))
        gunicorn_config = config.get('gunicorn', {})
        gunicorn_env = ['worker_class', 'threads', 'workers']
        if workers is not None:
            gunicorn_config['workers'] = workers

        for k in gunicorn_env:
            if get_env(k) in os.environ:
                gunicorn_config[k] = os.environ[get_env(k)]
        if server == 'flask' and 'worker_class' in gunicorn_config:
            if 'uvicorn' in gunicorn_config['worker_class']:
                logger.warning("Can't use flask with uvicorn. change to gthread")
                gunicorn_config['worker_class'] = 'gthread'
        
        GunicornWrapper(server, bind=bind, **gunicorn_config).run()
    elif wrapper == 'hypercorn' and server == 'quart':
        from mlchain.server.quart_server import QuartServer
        app = get_model(entry_file, serve_model=True)
        app = QuartServer(app, name=name, version=version, api_format=api_format,
                          authentication=authentication,
                          static_url_path=static_url_path,
                          static_folder=static_folder,
                          template_folder=template_folder)
        app.run(host, port, bind=bind, cors=cors,
                gunicorn=False, hypercorn=True, **config.get('hypercorn', {}), model_id=model_id)

    app = get_model(entry_file)
    if isinstance(app, MLServer):
        if app.__class__.__name__ == 'FlaskServer':
            app.run(host, port, cors=cors, gunicorn=False)
        elif app.__class__.__name__ == 'QuartServer':
            app.run(host, port, cors=cors, gunicorn=False, hypercorn=False)
        elif app.__class__.__name__ == 'GrpcServer':
            app.run(host, port)
    elif isinstance(app, ServeModel):
        if server not in ['quart', 'grpc']:
            server = 'flask'
        if server == 'flask':
            from mlchain.server.flask_server import FlaskServer
            app = FlaskServer(app, name=name, api_format=api_format,
                              version=version,
                              authentication=authentication,
                              static_url_path=static_url_path,
                              static_folder=static_folder,
                              template_folder=template_folder)
            app.run(host, port, cors=cors, gunicorn=False, model_id=model_id, threads=workers > 1)
        elif server == 'quart':
            from mlchain.server.quart_server import QuartServer
            app = QuartServer(app, name=name, api_format=api_format,
                              version=version,
                              authentication=authentication,
                              static_url_path=static_url_path,
                              static_folder=static_folder,
                              template_folder=template_folder)
            app.run(host, port, cors=cors, gunicorn=False,
                    hypercorn=False, model_id=model_id, workers=workers)

        elif server == 'grpc':
            from mlchain.server.grpc_server import GrpcServer
            app = GrpcServer(app, name=name)
            app.run(host, port)


def get_model(module, serve_model=False):
    import_name = prepare_import(module)

    module = importlib.import_module(import_name)
    serve_models = [v for v in module.__dict__.values() if isinstance(v, ServeModel)]
    if len(serve_models) > 0 and serve_model:
        serve_model = serve_models[0]
        return serve_model
    apps = [v for v in module.__dict__.values() if isinstance(v, MLServer)]
    if len(apps) > 0:
        return apps[0]
    if len(serve_models) > 0:
        return serve_models[0]

    # Could not find model 
    logger.debug("Could not find ServeModel")
    serve_models = [v for v in module.__dict__.values() if not isinstance(v, type)]
    if len(serve_models) > 0 and serve_model:
        serve_model = ServeModel(serve_models[-1])
        return serve_model

    logger.error("Could not find any instance to serve")
    return None
