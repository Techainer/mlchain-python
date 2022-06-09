import os
import click
import importlib
import sys
import copy
import GPUtil
import logging
from mlchain import logger
from mlchain.server import MLServer
from mlchain.base import ServeModel
from mlchain.server.authentication import Authentication
import traceback
from starlette.middleware.cors import CORSMiddleware

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
    return "GUNICORN_" + _k.upper()


op_config = click.option("--config", "-c", default=None, help="A json or yaml file")
op_name = click.option("--name", "-n", default=None, help="Name of the service")
op_host = click.option("--host", "-h", default=None, help="The host to run the server")
op_port = click.option("--port", "-p", default=None, help="The port to run the server")
op_bind = click.option("--bind", "-b", required=False, multiple=True, help="Gunicorn bind")
op_gunicorn = click.option("--gunicorn", "wrapper", flag_value="gunicorn", help="Run server with gunicorn or not")
op_flask = click.option("--flask", "server", flag_value="flask", help="Run with Flask server")
op_starlette = click.option("--starlette", "server", flag_value="starlette", help="Run with Starlette server")
op_worker = click.option("--workers", "-w", "workers", default=None, type=int, help="Number of workers")
op_thread = click.option("--threads", "-t", "threads", default=None, type=int, help="Number of threads")
op_mode = click.option("--mode", "-m", "mode", default=None, type=str, help="The mode of mlconfig")
op_api_format = click.option("--api_format", "-a", "api_format", default=None, type=str, help="Change the API Format class")
op_debug = click.option('--debug', '-d', is_flag=True, help="Debug or not")
op_preload = click.option('--preload', '-pre', is_flag=True, help="Run worker in preload mode")
@click.command(
    "run",
    short_help="Run a development server.",
    context_settings={"ignore_unknown_options": True},
)
@click.argument("entry_file", nargs=1, required=False, default=None)
@op_host
@op_port
@op_bind
@op_gunicorn
@op_flask
@op_starlette
@op_worker
@op_thread
@op_config
@op_name
@op_mode
@op_api_format
@op_debug
@op_preload
@click.option("--ngrok/--no-ngrok", default=False, type=bool)
@click.argument("kws", nargs=-1)
def run_command(
    entry_file,
    host,
    port,
    bind,
    wrapper,
    server,
    workers,
    threads,
    config,
    name,
    mode,
    api_format,
    debug,
    preload,
    ngrok,
    kws,
):
    kws = list(kws)

    ############
    # Get Config File
    ############

    if isinstance(entry_file, str) and not os.path.exists(entry_file):
        kws = [f"--entry_file={entry_file}"] + kws
        entry_file = None
    from mlchain import config as mlconfig
    from mlchain import mlconfig as mlchain_config

    default_config = False

    if config is None:
        default_config = True
        config = "mlconfig.yaml"

    config_path = copy.deepcopy(config)
    if os.path.isfile(config_path) and os.path.exists(config_path):
        config = mlconfig.load_file(config_path)
        if config is None:
            raise SystemExit("Config file {0} are not supported".format(config_path))
    else:
        if not default_config:
            raise SystemExit("Can't find config file {0}".format(config_path))
        else:
            raise SystemExit(
                "Can't find mlchain config file. Please double check your current working directory. Or use `mlchain init` to initialize a new ones here."
            )
    if "mode" in config and "env" in config["mode"]:
        if mode in config["mode"]["env"]:
            config["mode"]["default"] = mode
        elif mode is not None:
            available_mode = list(config["mode"]["env"].keys())
            available_mode = [each for each in available_mode if each != "default"]
            raise SystemExit(
                f"No {mode} mode are available. Found these mode in config file: {available_mode}"
            )
    mlconfig.load_config(config)

    ############
    # End Get Config File
    ############

    ############
    # Get Additional Params
    ############

    for kw in kws:
        if kw.startswith("--"):
            tokens = kw[2:].split("=", 1)
            if len(tokens) == 2:
                key, value = tokens
                mlconfig.mlconfig.update({key: value})
            else:
                raise AssertionError("Unexpected param {0}".format(kw))
        else:
            raise AssertionError("Unexpected param {0}".format(kw))

    ############
    # End Get Additional Params
    ############

    ############
    # Get host, port, entry file
    ############
    model_id = mlconfig.get_value(None, config, "model_id", None)
    entry_file = mlconfig.get_value(entry_file, config, "entry_file", "server.py")
    if entry_file.strip() == "":
        raise SystemExit(f"Entry file cannot be empty")
    if not os.path.exists(entry_file):
        raise SystemExit(
            f"Entry file {entry_file} not found in current working directory."
        )
    host = mlconfig.get_value(host, config, "host", "localhost")
    port = mlconfig.get_value(port, config, "port", 5000)
    server = mlconfig.get_value(server, config, "server", "starlette").lower()
    if len(bind) == 0:
        bind = None
    bind = mlconfig.get_value(bind, config, "bind", [])
    bind = list(bind)

    wrapper = mlconfig.get_value(wrapper, config, "wrapper", None)
    if wrapper == "gunicorn" and os.name == "nt":
        logger.warning(
            "Gunicorn warper are not supported on Windows. Switching to None instead."
        )
        wrapper = None
    ############
    # End Get host, port, entry file
    ############


    ############
    # Get workers and threads
    ############
    if "gunicorn" in config:
        if "workers" in config["gunicorn"] and workers is None:
            workers = config["gunicorn"]["workers"]
        
        if mlchain_config.gunicorn_workers is not None:
            workers = mlchain_config.gunicorn_workers

    if "gunicorn" in config:
        if "threads" in config["gunicorn"] and threads is None:
            threads = config["gunicorn"]["threads"]
        
        if mlchain_config.gunicorn_threads is not None:
            threads = mlchain_config.gunicorn_threads
    ############
    # End Get workers and threads
    ############

    ############
    # Get name, version and cors
    ############
    name = mlconfig.get_value(name, config, "name", None)
    version = mlconfig.get_value(None, config, "version", "0.0")
    version = str(version)

    cors = mlconfig.get_value(None, config, "cors", True)
    cors_allow_origins = mlconfig.get_value(None, config, "cors_allow_origins", ['*'])
    ############
    # End Get name, version and cors
    ############

    ############
    # Get static
    ############
    static_folder = mlconfig.get_value(None, config, "static_folder", None)
    static_url_path = mlconfig.get_value(None, config, "static_url_path", "static")
    template_folder = mlconfig.get_value(None, config, "template_folder", None)
    ############
    # End Get static
    ############

    ############
    # Get API format and keys
    ############
    api_format = mlconfig.get_value(api_format, config, "api_format", None)
    api_keys = os.getenv("API_KEYS", None)
    if api_keys is not None:
        api_keys = api_keys.split(";")
    api_keys = mlconfig.get_value(api_keys, config, "api_keys", None)
    if api_keys is None:
        authentication = None
    else:
        authentication = Authentication(api_keys)
    ############
    # End Get API format and keys
    ############

    if debug: 
        logger.setLevel(logging.DEBUG)


    ############
    # Run with ngrok 
    ############
    if ngrok:
        from pyngrok import ngrok as pyngrok

        endpoint = pyngrok.connect(port=port)
        logger.info("Ngrok url: {0}".format(endpoint))
        os.environ["NGROK_URL"] = endpoint

    if wrapper == "gunicorn":
        ############
        # Run with gunicorn 
        ############
        from gunicorn.app.base import BaseApplication

        gpus = select_gpu()

        class GunicornWrapper(BaseApplication):
            def __init__(self, server_, **kwargs):
                assert server_.lower() in [
                    "starlette",
                    "flask",
                ], "Server name is only starlette or flask"
                self.server = server_.lower()
                self.options = kwargs
                self.autofrontend = False
                super(GunicornWrapper, self).__init__()

            def load_config(self):
                config = {
                    key: value
                    for key, value in self.options.items()
                    if key in self.cfg.settings and value is not None
                }
                for key, value in config.items():
                    self.cfg.set(key.lower(), value)

                from mlchain.base.gunicorn_config import post_worker_init

                self.cfg.set("post_worker_init", post_worker_init)

            def load(self):
                original_cuda_variable = os.environ.get("CUDA_VISIBLE_DEVICES")
                if original_cuda_variable is None:
                    os.environ["CUDA_VISIBLE_DEVICES"] = str(next(gpus))
                else:
                    logger.info(
                        f"Skipping automatic GPU selection for gunicorn worker since CUDA_VISIBLE_DEVICES environment variable is already set to {original_cuda_variable}"
                    )
                serve_model = get_model(entry_file, serve_model=True)

                if serve_model is None:
                    raise Exception(
                        f"Can not init model class from {entry_file}. Please check mlconfig.yaml or {entry_file} or mlchain run -m {{mode}}!"
                    )

                if isinstance(serve_model, ServeModel):
                    if (not self.autofrontend) and model_id is not None:
                        from mlchain.server.autofrontend import register_autofrontend

                        register_autofrontend(
                            model_id,
                            serve_model=serve_model,
                            version=version,
                            endpoint=os.getenv("NGROK_URL"),
                        )
                        self.autofrontend = True

                    if self.server == "flask":
                        from mlchain.server.flask_server import FlaskServer

                        app = FlaskServer(
                            serve_model,
                            name=name,
                            api_format=api_format,
                            version=version,
                            authentication=authentication,
                            static_url_path=static_url_path,
                            static_folder=static_folder,
                            template_folder=template_folder,
                        )
                        if cors:
                            from flask_cors import CORS

                            CORS(app.app, origins=cors_allow_origins)
                        return app.app
                    if self.server == "starlette":
                        from mlchain.server.starlette_server import StarletteServer

                        app = StarletteServer(
                            serve_model,
                            name=name,
                            api_format=api_format,
                            version=version,
                            authentication=authentication,
                            static_url_path=static_url_path,
                            static_folder=static_folder,
                            template_folder=template_folder,
                        )
                        if debug:
                            app.app._debug = debug
                        if cors:
                            app.app.add_middleware(CORSMiddleware, allow_origins=cors_allow_origins)
                        return app.app
                return None

        if host is not None and port is not None:
            bind.append("{0}:{1}".format(host, port))

        bind = list(set(bind))

        ###
        # Set the workers, threads and worker_class to run 
        ###
        gunicorn_config = config.get("gunicorn", {})
        gunicorn_env = ["worker_class", "threads", "workers"]
        if debug: 
            gunicorn_config['loglevel'] = "debug"
        if workers is not None:
            gunicorn_config["workers"] = workers
        gunicorn_config['preload_app'] = preload
        if threads is not None:
            gunicorn_config["threads"] = threads
        
        for k in gunicorn_env:
            if get_env(k) in os.environ:
                gunicorn_config[k] = os.environ[get_env(k)]
        ###
        # End Set the workers, threads and worker_class to run 
        ###
        
        if server == "flask":
            if "worker_class" in gunicorn_config:
                if "uvicorn" in gunicorn_config["worker_class"]:
                    logger.warning("Can't use Flask with uvicorn. change to gthread")
                    gunicorn_config["worker_class"] = "gthread"
            else: 
                logger.debug("Using gthread with Flask")
                gunicorn_config["worker_class"] = "gthread"
        if server == "starlette":
            if "worker_class" in gunicorn_config:
                if gunicorn_config["worker_class"] != "uvicorn.workers.UvicornWorker": 
                    logger.warning("Can't use Starlette with {0}. change to uvicorn.workers.UvicornWorker".format(gunicorn_config["worker_class"]))
                    gunicorn_config["worker_class"] = "uvicorn.workers.UvicornWorker"
            else: 
                logger.warning("Using uvicorn.workers.UvicornWorker with Starlette")
                gunicorn_config["worker_class"] = "uvicorn.workers.UvicornWorker"

        GunicornWrapper(server, bind=bind, **gunicorn_config).run()
    elif server == "starlette":
        ############
        # Run with starlette 
        ############
        from mlchain.server.starlette_server import StarletteServer

        app = get_model(entry_file, serve_model=True)

        if app is None:
            raise Exception(
                "Can not init model class from {0}. Please check mlconfig.yaml or {0} or mlchain run -m {{mode}}!".format(
                    entry_file
                )
            )

        app = StarletteServer(
            app,
            name=name,
            version=version,
            api_format=api_format,
            authentication=authentication,
            static_url_path=static_url_path,
            static_folder=static_folder,
            template_folder=template_folder,
        )
        app.run(host, port, bind=bind, cors=cors, cors_allow_origins=cors_allow_origins, gunicorn=True, debug=debug, model_id=model_id)

    app = get_model(entry_file)

    if app is None:
        raise Exception(
            "Can not init model class from {0}. Please check mlconfig.yaml or {0} or mlchain run -m {{mode}}!".format(
                entry_file
            )
        )

    if isinstance(app, MLServer):
        if app.__class__.__name__ == "FlaskServer":
            app.run(host, port, cors=cors, cors_allow_origins=cors_allow_origins, gunicorn=False, debug=debug)
        elif app.__class__.__name__ == "StarletteServer":
            app.run(host, port, cors=cors, cors_allow_origins=cors_allow_origins, debug=debug)
        elif app.__class__.__name__ == "GrpcServer":
            app.run(host, port, debug=debug)
    elif isinstance(app, ServeModel):
        if server != "starlette":
            server = "flask"
        if server == "flask":
            from mlchain.server.flask_server import FlaskServer

            app = FlaskServer(
                app,
                name=name,
                api_format=api_format,
                version=version,
                authentication=authentication,
                static_url_path=static_url_path,
                static_folder=static_folder,
                template_folder=template_folder,
            )
            app.run(
                host,
                port,
                cors=cors,
                cors_allow_origins=cors_allow_origins,
                gunicorn=False,
                model_id=model_id,
                threads=threads, 
                debug=debug
            )
        elif server == "starlette":
            from mlchain.server.starlette_server import StarletteServer

            app = StarletteServer(
                app,
                name=name,
                api_format=api_format,
                version=version,
                authentication=authentication,
                static_url_path=static_url_path,
                static_folder=static_folder,
                template_folder=template_folder,
            )
            app.run(
                host,
                port,
                cors=cors,
                cors_allow_origins=cors_allow_origins,
                gunicorn=True,
                model_id=model_id,
                workers=workers,
                threads=threads, 
                debug=debug
            )

def get_model(module, serve_model=False):
    """
    Get the serve_model from entry_file
    """
    import_name = prepare_import(module)

    try:
        module = importlib.import_module(import_name)
    except Exception as ex:
        logger.error(traceback.format_exc())
        return None

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

    logger.error(
        "Could not find any instance to serve. So please check again the mlconfig.yaml or server file!"
    )
    return None
