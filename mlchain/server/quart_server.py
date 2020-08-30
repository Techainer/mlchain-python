import importlib
import sys
import inspect
import time
import os
from collections import defaultdict
from typing import Union
from quart import Quart, request, Response, jsonify, render_template, Blueprint, send_from_directory, send_file
from quart.exceptions import RequestEntityTooLarge
from quart.datastructures import FileStorage
from quart_cors import cors as CORS
import mlchain
from mlchain.base.serve_model import ServeModel
from mlchain.base.log import logger, format_exc
from mlchain.base.exceptions import MlChainError
from mlchain.base.wrapper import GunicornWrapper, HypercornWrapper
from .base import MLServer, Converter, RawResponse, FileResponse, TemplateResponse
from .format import RawFormat
from .swagger import SwaggerTemplate
from .view import ViewAsync
from .autofrontend import register_autofrontend

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'server/templates')
STATIC_PATH = os.path.join(APP_PATH, 'server/static')


class QuartEndpointAction:
    """
    Defines an Quart Endpoint for a specific action for any client.
    """

    def __init__(self, action, serializers_dict, version='latest', api_keys=None):
        """
        Create the endpoint by specifying which action we want the endpoint to perform, at each call
        :param action: The function to execute on endpoint call
        """
        # Defines which action (which function) should be called
        assert callable(action)

        self.action = action
        self.serializers_dict = serializers_dict
        self.version = version
        self.json_serializer = self.serializers_dict['application/json']
        self.msgpack_serializer = self.serializers_dict['application/msgpack']
        self.msgpack_blosc_serializer = self.serializers_dict['application/msgpack_blosc']
        self.api_keys = api_keys

    async def __get_json_response(self, output, status=200):
        """
        Get JSON Reponse
        """
        output_encoded = self.json_serializer.encode(output)
        return Response(output_encoded, mimetype='application/json', status=status)

    async def __get_msgpack_response(self, output, status=200):
        """
        Get msgpack Reponse
        """
        output_encoded = self.msgpack_serializer.encode(output)
        return Response(output_encoded, mimetype='application/msgpack', status=status)

    async def __get_msgpack_blosc_response(self, output, status=200):
        """
        Get msgpack blosc response
        """
        output_encoded = self.msgpack_blosc_serializer.encode(output)
        return Response(output_encoded, mimetype='application/msgpack_blosc', status=status)

    async def __call__(self, *args, **kwargs):
        """
        Standard method that effectively perform the stored action of this endpoint.
        :param args: Arguments to give to the stored function
        :param kwargs: Keywords Arguments to give to the stored function
        :return: The response, which is a jsonified version of the function returned value
        """
        start_time = time.time()

        # If data POST is in msgpack format
        content_type = request.content_type
        if content_type not in self.serializers_dict:
            headers = {k.upper(): v for k, v in request.headers.items()}
            'SERIALIZER'
            if 'SERIALIZER'.upper() in headers:
                content_type = headers['SERIALIZER']
            else:
                content_type = 'application/json'

        serializer = self.serializers_dict.get(content_type,
                                               self.serializers_dict['application/json'])
        if content_type == 'application/msgpack':
            response_function = self.__get_msgpack_response
        elif content_type == 'application/msgpack_blosc':
            response_function = self.__get_msgpack_blosc_response
        else:
            response_function = self.__get_json_response
        if request.method == 'POST' and self.api_keys is not None or (
                isinstance(self.api_keys, (list, dict)) and len(self.api_keys) > 0):
            authorized = False
            has_key = False
            for key in ['x-api-key', 'apikey', 'apiKey', 'api-key']:
                apikey = request.headers.get(key, '')
                if apikey != '':
                    has_key = True
                if apikey in self.api_keys:
                    authorized = True
                    break
            if not authorized:
                if has_key:
                    error = 'Unauthorized. Api-key incorrect.'
                else:
                    error = 'Unauthorized. Lack of x-api-key or apikey or api-key in headers.'
                output = {
                    'error': error,
                    'api_version': self.version,
                    'mlchain_version': mlchain.__version__
                }
                return await response_function(output, 401)
        try:
            # Perform the action
            if inspect.iscoroutinefunction(self.action) \
                    or (not inspect.isfunction(self.action)
                        and hasattr(self.action, '__call__')
                        and inspect.iscoroutinefunction(self.action.__call__)):
                if request.method == 'POST':
                    output = await self.action(*args, **kwargs, serializer=serializer)
                else:
                    output = await self.action(*args, **kwargs)
            else:
                if request.method == 'POST':
                    output = self.action(*args, **kwargs, serializer=serializer)
                else:
                    output = self.action(*args, **kwargs)

            if isinstance(output, RawResponse):
                output = Response(output.response, status=output.status,
                                  headers=output.headers,
                                  mimetype=output.mimetype,
                                  content_type=output.content_type)
                output.headers['mlchain_version'] = mlchain.__version__
                output.headers['api_version'] = self.version
                return output

            if isinstance(output, FileResponse):
                file = await send_file(output.path)
                for k, v in output.headers.items():
                    file.headers[k] = v
                file.headers['mlchain_version'] = mlchain.__version__
                file.headers['api_version'] = self.version
                return file

            if isinstance(output, Response):
                return output

            output = {
                'output': output,
                'time': round(time.time() - start_time, 2),
                'api_version': self.version,
                'mlchain_version': mlchain.__version__
            }

            return await response_function(output, 200)
        except MlChainError as ex:
            err = ex.msg
            logger.error("code: {0} msg: {1}".format(ex.code, ex.msg))

            output = {
                'error': err,
                'time': round(time.time() - start_time, 2),
                'code': ex.code,
                'api_version': self.version,
                'mlchain_version': mlchain.__version__
            }
            return await response_function(output, ex.status_code)
        except AssertionError as ex:
            err = str(ex)
            logger.error(err)

            output = {
                'error': err,
                'time': round(time.time() - start_time, 2),
                'api_version': self.version,
                'mlchain_version': mlchain.__version__
            }
            return await response_function(output, 422)
        except Exception as ex:
            err = str(format_exc(name='mlchain.serve.server'))
            logger.error(err)

            output = {
                'error': err,
                'time': round(time.time() - start_time, 2),
                'api_version': self.version,
                'mlchain_version': mlchain.__version__
            }
            return await response_function(output, 500)


class QuartView(ViewAsync):
    def __init__(self, server, formatter=None, authentication=None):
        ViewAsync.__init__(self, server, formatter, authentication)

    async def parse_data(self):
        try:
            headers = request.headers
            # Parse form
            temp = await request.form
            form = defaultdict(list)
            for k, v in temp.items():
                form[k].append(v)
            
            # Parse Params 
            temp = request.args
            for k, v in temp.items():
                form[k].append(v)

            # Parse Files 
            temp = await request.files
            files = defaultdict(list)
            for k, v in temp.items():
                files[k].append(v)
            data = await request.data
            return headers, form, files, data
        except RequestEntityTooLarge:
            raise MlChainError("Request too large", status_code=413)
        except:
            raise

    async def make_response(self, response: Union[RawResponse, FileResponse]):
        if isinstance(response, RawResponse):
            output = Response(response.response, status=response.status,
                              headers=response.headers,
                              mimetype=response.mimetype,
                              content_type=response.content_type)
            output.headers['mlchain_version'] = mlchain.__version__
            output.headers['api_version'] = self.server.version
            return output

        if isinstance(response, FileResponse):
            file = await send_file(response.path)
            for k, v in response.headers.items():
                file.headers[k] = v
            file.headers['mlchain_version'] = mlchain.__version__
            file.headers['api_version'] = self.server.version
            return file

        if isinstance(response, TemplateResponse):
            return await render_template(response.template_name, **response.context)

        if isinstance(response, Response):
            return response

        raise Exception("make response must return RawResponse or FileResponse")


class QuartServer(MLServer):
    def __init__(self, model: ServeModel, name=None, version='0.0',
                 authentication=None, api_format=None,
                 static_folder=None, template_folder=None, static_url_path=None):
        MLServer.__init__(self, model, name)
        self.app = Quart(self.name, static_folder=static_folder,
                         template_folder=template_folder,
                         static_url_path=static_url_path)
        self.app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024
        self.app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

        self.version = version
        self.converter = Converter(FileStorage, self._get_file_name, self._get_data)
        self.authentication = authentication
        self.register_home()
        self._initalize_app()
        if isinstance(api_format, str):
            try:
                package, class_name = api_format.rsplit('.', 1)
                api_format = importlib.import_module(package)
                api_format = getattr(api_format, class_name)
            except:
                api_format = None
        if isinstance(api_format, type):
            api_format = api_format()

        self.api_format = '{0}.{1}'.format(api_format.__class__.__module__,
                                           api_format.__class__.__name__)
        self.app.add_url_rule('/call/<function_name>', 'call',
                              QuartView(self, api_format, self.authentication),
                              methods=['POST', 'GET'], strict_slashes=False)
        self.app.add_url_rule('/call_raw/<function_name>', 'call_raw',
                              QuartView(self, RawFormat(), self.authentication),
                              methods=['POST', 'GET'], strict_slashes=False)

    def register_home(self):
        home_ui = Blueprint("home", __name__, static_folder=STATIC_PATH,
                            template_folder=TEMPLATE_PATH,
                            static_url_path="/home_static")

        @home_ui.route("/", methods=['GET'])
        def home():
            return render_template("home.html", base_prefix=os.getenv('BASE_PREFIX', ''))

        self.app.register_blueprint(home_ui)

    def _get_file_name(self, storage):
        return storage.filename

    def _get_data(self, storage):
        return storage.read()

    def _add_endpoint(self, endpoint=None, endpoint_name=None,
                      handler=None, methods=['GET', 'POST']):
        """
        Add one endpoint to the flask application. Accept GET, POST and PUT.
        :param endpoint: Callable URL.
        :param endpoint_name: Name of the Endpoint
        :param handler: function to execute on call on the URL
        :return: Nothing
        """
        self.app.add_url_rule(endpoint, endpoint_name,
                              QuartEndpointAction(handler,
                                                  self.serializers_dict,
                                                  version=self.version,
                                                  api_keys=None),
                              methods=methods)

    def register_swagger(self):
        swagger_ui = Blueprint("swagger", __name__,
                               static_folder=os.path.join(TEMPLATE_PATH, 'swaggerui'))

        swagger_template = SwaggerTemplate(os.getenv("BASE_PREFIX", '/'),
                                           [{'name': self.name}],
                                           title=self.name,
                                           description=self.model.model.__doc__,
                                           version=self.model.name)
        for name, func in self.model.get_all_func().items():
            swagger_template.add_endpoint(func, f'/call/{name}', tags=[self.name])

        SWAGGER_URL = '/swagger'

        @swagger_ui.route('{0}/'.format(SWAGGER_URL))
        @swagger_ui.route('{0}/<path:path>'.format(SWAGGER_URL))
        def swagger_endpoint(path=None):
            if path is None:
                return send_from_directory(
                    swagger_ui._static_folder,
                    "index.html"
                )
            if path == 'swagger.json':
                return jsonify(swagger_template.template)
            if isinstance(path, str):
                path = path.strip('.')
            return send_from_directory(
                swagger_ui._static_folder,
                path
            )

        self.app.register_blueprint(swagger_ui)

    def run(self, host='127.0.0.1', port=8080, bind=None,
            cors=False, cors_allow_origins="*", gunicorn=False, hypercorn=True,
            debug=False, use_reloader=False, workers=1, timeout=60, keepalive=5,
            max_requests=0, threads=1, worker_class='asyncio', umask='0', ngrok=False, model_id=None, **kwargs):
        """
        Run a server from a Python class
        :model: Your model class
        :host: IP address you want to start server
        :port: Port to start server at
        :bind: Gunicorn: The socket to bind. A list of string or string of the form: HOST, HOST:PORT, unix:PATH, fd://FD. An IP is a valid HOST.
        :deny_all_function: Default is False, which enable all function except function with @except_serving or function in blacklist, True is deny all and you could use with whitelist
        :blacklist: All listing function name here won't be served
        :whitelist: Served all function name inside whitelist
        :cors: Enable CORS or not
        :cors_resources: Config Resources of flask-cors
        :cors_allow_origins: Allow host of cors
        :gunicorn: Run with Gunicorn or not
        :debug: Debug or not
        :use_reloader: Default False, which is using 1 worker in debug instead of 2
        :timeout: Timeout of each request
        :keepalive: The number of seconds to wait for requests on a Keep-Alive connection.
        :threads: The number of worker threads for handling requests. Be careful, threads would break your result if it is bigger than 1
        :worker_class: The type of workers to use.
        :max_requests: Max Request to restart Gunicorn Server, default is 0 which means no restart
        :umask: A bit mask for the file mode on files written by Gunicorn.
        :kwargs: Other Gunicorn options
        """
        if not ((sys.version_info.major == 3 and sys.version_info.minor >= 6)
                or sys.version_info.major > 3):
            raise Exception("Quart must be use with Python 3.7 or higher")

        if not isinstance(bind, list) and not isinstance(bind, str) and bind is not None:
            raise AssertionError(
                "Bind have to be list or string of the form: HOST, HOST:PORT, unix:PATH, fd://FD. An IP is a valid HOST.")

        try:
            self.register_swagger()
        except Exception as ex:
            logger.error("Can't register swagger with error {0}".format(ex))

        if ngrok:
            from pyngrok import ngrok as pyngrok
            endpoint = pyngrok.connect(port=port)
            logger.info("Ngrok url: {0}".format(endpoint))
            os.environ['NGROK_URL'] = endpoint
        else:
            endpoint = os.environ.get('NGROK_URL')

        try:
            register_autofrontend(model_id=model_id, serve_model=self.model,
                                  version=self.version,
                                  endpoint=endpoint)
        except Exception as ex:
            logger.error("Can't register autofrontend with error {0}".format(ex))

        if cors:
            CORS(self.app, allow_origin=cors_allow_origins)

        if not gunicorn and not hypercorn:
            if bind is not None:
                logger.warning("Quart only use host and port to run, not bind")

            logger.info("-" * 80)
            logger.info("Served model with Quart at host={0}, port={1}".format(host, port))
            logger.info("Debug = {}".format(debug))
            logger.info("-" * 80)

            self.app.run(host=host, port=port, debug=debug, use_reloader=use_reloader)
        elif hypercorn:
            # Process bind, host, port
            if isinstance(bind, str):
                bind = [bind]

            bind_host_port = '%s:%s' % (host, port)
            if not bind:
                bind = [bind_host_port]

            logger.info("-" * 80)
            logger.info("Served model with Quart and Hypercorn at bind={}".format(bind))
            logger.warning("timeout, threads, max_requests is not work here")
            if 'uvloop' not in worker_class:
                logger.info("You could use worker_class=uvloop for better performance. It isn't work on Windows")
            logger.info("Number of workers: {}".format(workers))
            logger.info("Debug = {}".format(debug))
            logger.info("-" * 80)

            loglevel = kwargs.get('loglevel', 'warning' if debug else 'info')
            HypercornWrapper(self.app, bind=bind, workers=workers,
                             keep_alive_timeout=keepalive, loglevel=loglevel,
                             worker_class=worker_class,
                             umask=int(umask), **kwargs).run()
        else:
            # Process bind, host, port
            if isinstance(bind, str):
                bind = [bind]

            bind_host_port = '%s:%s' % (host, port)
            if bind is None:
                bind = [bind_host_port]

            worker_class = 'uvicorn.workers.UvicornWorker'

            logger.info("-" * 80)
            logger.info("Served model with Quart and Gunicorn at bind={}".format(bind))
            logger.info("Number of workers: {}".format(workers))
            logger.info("Number of threads: {}".format(threads))
            logger.info("API timeout: {}".format(timeout))
            logger.info("Debug = {}".format(debug))
            logger.info("-" * 80)

            loglevel = kwargs.get('loglevel', 'warning' if debug else 'info')
            GunicornWrapper(self.app, bind=bind, workers=workers, timeout=timeout,
                            keepalive=keepalive, max_requests=max_requests,
                            loglevel=loglevel, threads=threads,
                            worker_class=worker_class, umask=umask, **kwargs).run()
