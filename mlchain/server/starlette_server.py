import sys
import inspect
import time
import os
from collections import defaultdict
from typing import Union
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
import mlchain
from mlchain.base.serve_model import ServeModel
from mlchain.base.log import logger, format_exc
from mlchain.base.exceptions import MlChainError, MLChainConfigError
from mlchain.base.wrapper import GunicornWrapper
from .base import AsyncMLServer, AsyncConverter, RawResponse, FileResponse, TemplateResponse
from .format import RawFormat
from .swagger import SwaggerTemplate
from .view import StarletteAsyncView
from .autofrontend import register_autofrontend
from starlette.datastructures import UploadFile
from mlchain import mlchain_context
from starlette.responses import FileResponse as StarletteFileResponse
from sentry_sdk import push_scope, start_transaction
from mlchain import mlconfig
from uuid import uuid4

APP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_PATH = os.path.join(APP_PATH, 'server/templates')
SWAGGER_PATH = os.path.join(TEMPLATE_PATH, 'swaggerui')
STATIC_PATH = os.path.join(APP_PATH, 'server/static')

class StarletteEndpointAction:
    """
    Defines an Starlette Endpoint for a specific action for any client.
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

    def __get_json_response(self, output, status=200):
        """
        Get JSON Reponse
        """
        output_encoded = self.json_serializer.encode(output)
        return Response(output_encoded, media_type='application/json', status_code=status)

    def __get_msgpack_response(self, output, status=200):
        """
        Get msgpack Reponse
        """
        output_encoded = self.msgpack_serializer.encode(output)
        return Response(output_encoded, media_type='application/msgpack', status_code=status)

    def __get_msgpack_blosc_response(self, output, status=200):
        """
        Get msgpack blosc response
        """
        output_encoded = self.msgpack_blosc_serializer.encode(output)
        return Response(output_encoded, media_type='application/msgpack_blosc', status_code=status)

    def init_context(self): 
        uid = str(uuid4())
        mlchain_context['MLCHAIN_CONTEXT_ID'] = uid
        return uid 

    async def __call__(self, scope, receive, send, *args, **kwargs): 
        """
        Standard method that effectively perform the stored action of this endpoint.
        :param args: Arguments to give to the stored function
        :param kwargs: Keywords Arguments to give to the stored function
        :return: The response, which is a jsonified version of the function returned value
        """
        start_time = time.time()

        with push_scope() as sentry_scope:
            transaction_name = "{0}  ||  {1}".format(mlconfig.MLCHAIN_SERVER_NAME, self.action.__name__)
            sentry_scope.transaction = transaction_name
            
            with start_transaction(op="task", name=transaction_name):
                uid = self.init_context()

                request = Request(scope, receive)
                kwargs.update(request.path_params)

                # If data POST is in msgpack format
                content_type = request.headers.get('content-type', 'application/json')
                if content_type not in self.serializers_dict:
                    headers = {k.upper(): v for k, v in request.headers.items()}

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
                            'mlchain_version': mlchain.__version__,
                            "request_id": mlchain_context.MLCHAIN_CONTEXT_ID
                        }
                        return await response_function(output, 401)(scope, receive, send)
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
                        output = Response(output.response, status_code=output.status,
                                        headers=output.headers,
                                        media_type=output.mimetype,
                                        content_type=output.content_type)
                        output.headers['mlchain_version'] = mlchain.__version__
                        output.headers['api_version'] = self.version
                        output.headers['request_id'] = mlchain_context.MLCHAIN_CONTEXT_ID
                        return await output(scope, receive, send)

                    if isinstance(output, FileResponse):
                        file = await StarletteFileResponse(output.path)
                        for k, v in output.headers.items():
                            file.headers[k] = v
                        file.headers['mlchain_version'] = mlchain.__version__
                        file.headers['api_version'] = self.version
                        file.headers['request_id'] = mlchain_context.MLCHAIN_CONTEXT_ID
                        return await file(scope, receive, send)

                    if isinstance(output, Response):
                        return await output(scope, receive, send)

                    output = {
                        'output': output,
                        'time': round(time.time() - start_time, 2),
                        'api_version': self.version,
                        'mlchain_version': mlchain.__version__,
                        "request_id": mlchain_context.MLCHAIN_CONTEXT_ID
                    }
                    
                    return await response_function(output, 200)(scope, receive, send)
                except MlChainError as ex:
                    err = ex.msg
                    # logger.error("code: {0} msg: {1}".format(ex.code, ex.msg))

                    output = {
                        'error': err,
                        'time': round(time.time() - start_time, 2),
                        'code': ex.code,
                        'api_version': self.version,
                        'mlchain_version': mlchain.__version__,
                        "request_id": mlchain_context.MLCHAIN_CONTEXT_ID
                    }
                    return await response_function(output, ex.status_code)(scope, receive, send)
                except AssertionError as ex:
                    err = str(ex)

                    output = {
                        'error': err,
                        'time': round(time.time() - start_time, 2),
                        'api_version': self.version,
                        'mlchain_version': mlchain.__version__,
                        "request_id": mlchain_context.MLCHAIN_CONTEXT_ID
                    }
                    return await response_function(output, 422)(scope, receive, send)
                except Exception as ex:
                    err = format_exc(name='mlchain.serve.server')

                    output = {
                        'error': err,
                        'time': round(time.time() - start_time, 2),
                        'api_version': self.version,
                        'mlchain_version': mlchain.__version__,
                        "request_id": mlchain_context.MLCHAIN_CONTEXT_ID
                    }
                    return await response_function(output, 500)(scope, receive, send)


class StarletteView(StarletteAsyncView):
    def __init__(self, server, formatter=None, authentication=None):
        StarletteAsyncView.__init__(self, server, formatter, authentication)

    async def parse_data(self, request: Request):
        headers = request.headers
        files = defaultdict(list)
        form = defaultdict(list)

        # Parse form and files
        try:
            temp = await request.form()
        except:
            temp = {}

        for k, v in temp.items():
            if isinstance(v, UploadFile):
                files[k].append(v)
            else:
                form[k].append(v)

        # Parse Params 
        temp = request.query_params
        for k, v in temp.items():
            form[k].append(v)

        data = ""
        return headers, form, files, data

    async def __call__(self, scope, receive, send, *args, **kwargs): 
        request = Request(scope, receive)
        function_name = request.path_params['function_name']
        return await self.call_function(function_name, request, scope, receive, send, **kwargs)

    async def make_response(self, response: Union[RawResponse, FileResponse], request, scope, receive, send):
        if isinstance(response, RawResponse):
            output = Response(response.response, status_code=response.status,
                              headers=response.headers,
                              media_type=response.content_type)
            output.headers['mlchain_version'] = mlchain.__version__
            output.headers['api_version'] = self.server.version
            output.headers['request_id'] = mlchain_context.MLCHAIN_CONTEXT_ID
            return await output(scope, receive, send)

        if isinstance(response, FileResponse):
            file = StarletteFileResponse(response.path)
            for k, v in response.headers.items():
                file.headers[k] = v
            file.headers['mlchain_version'] = mlchain.__version__
            file.headers['api_version'] = self.server.version
            file.headers['request_id'] = mlchain_context.MLCHAIN_CONTEXT_ID
            return await file(scope, receive, send)

        if isinstance(response, TemplateResponse):
            if self.templates is None: 
                raise MLChainConfigError("Not found 'template_folder', please check the mlconfig.yaml!")
            return self.templates.TemplateResponse(response.template_name, {'request': request})

        if isinstance(response, Response):
            return await response(scope, receive, send)

        raise Exception("make_response must return RawResponse or FileResponse")

class StarletteServer(AsyncMLServer):
    def __init__(self, model: ServeModel, name=None, version='0.0',
                 authentication=None, api_format=None,
                 static_folder=None, template_folder=None, static_url_path:str="static"):
        AsyncMLServer.__init__(self, model, name, version, api_format)

        if not isinstance(static_url_path, str): 
            static_url_path = "static"
        self.app = Starlette(
            routes= [
                Mount('/{0}'.format(static_url_path.strip("/")), app=StaticFiles(directory=static_folder), name="static"),
                Mount('/call', routes=[
                    Route('/{function_name:path}', StarletteView(self, self.api_format_class, self.authentication), methods=['POST', 'GET'], name="call")
                ]),
                Mount('/call_raw', routes=[
                    Route('/{function_name:path}', StarletteView(self, RawFormat(), self.authentication), methods=['POST', 'GET'], name="call_raw")
                ]),
            ],
        )

        if template_folder is not None and isinstance(template_folder, str) and len(template_folder) > 0: 
            self.templates = Jinja2Templates(directory=template_folder)
        else: 
            self.templates = None
        self.mlchain_template = Jinja2Templates(directory=TEMPLATE_PATH)

        self.converter = AsyncConverter(UploadFile, self._get_file_name, self._get_data)

        self.initialize_endpoint()

    def _register_home(self):
        async def home(request: Request):
            return self.mlchain_template.TemplateResponse('home.html', {'request': request})

        self.app.mount("/home_static", StaticFiles(directory=STATIC_PATH), name="home_static")
        self.app.add_route(path="/", route=home, methods=['GET'], name="home")

    def _get_file_name(self, storage):
        return storage.filename

    async def _get_data(self, storage):
        return await storage.read()

    async def convert(self, value, out_type):
        """
        Convert the value in to out_type
        :value: The value
        :out_type: Expected type
        """
        return await self.converter.convert(value, out_type)
        
    def _add_endpoint(self, endpoint=None, endpoint_name=None,
                      handler=None, methods=['GET', 'POST']):
        """
        Add one endpoint to the flask application. Accept GET, POST and PUT.
        :param endpoint: Callable URL.
        :param endpoint_name: Name of the Endpoint
        :param handler: function to execute on call on the URL
        :return: Nothing
        """
        self.app.add_route(path=endpoint.replace("<", "{").replace(">", "}").replace("{function_name}", "{function_name:path}"), name=endpoint_name,
                              route=StarletteEndpointAction(handler,
                                                  self.serializers_dict,
                                                  version=self.version,
                                                  api_keys=None),
                              methods=methods)

    def _register_swagger(self):
        swagger_template = SwaggerTemplate(os.getenv("BASE_PREFIX", '/'),
                                           [{'name': self.name}],
                                           title=self.name,
                                           description=self.model.model.__doc__,
                                           version=self.model.name)
        for name, func in self.model.get_all_func().items():
            swagger_template.add_endpoint(func, f'/call/{name}', tags=["MlChain Format APIs"])
            swagger_template.add_endpoint(func, f'/call_raw/{name}', tags=["MlChain Raw Output APIs"])

        swagger_template.add_core_endpoint(self.model._get_parameters_of_func, '/api/get_params/{function_name}', tags=["MlChain Core APIs"])
        swagger_template.add_core_endpoint(self.model._get_description_of_func, '/api/des_func/{function_name}', tags=["MlChain Core APIs"])
        swagger_template.add_core_endpoint(self._check_status, '/api/ping', tags=["MlChain Core APIs"])
        swagger_template.add_core_endpoint(self.model._get_all_description, '/api/description', tags=["MlChain Core APIs"])
        swagger_template.add_core_endpoint(self.model._list_all_function, '/api/list_all_function', tags=["MlChain Core APIs"])
        swagger_template.add_core_endpoint(self.model._list_all_function_and_description, '/api/list_all_function_and_description', tags=["MlChain Core APIs"])

        SWAGGER_URL = 'swagger'

        async def swagger_home(request: Request):
            return self.mlchain_template.TemplateResponse('swaggerui/index.html', {'request': request})

        async def swagger_endpoint(request: Request):
            path = request.path_params['path']
            path = path.strip('.')
    
            if path == 'swagger.json':
                return JSONResponse(swagger_template.template)
            
            if path == "":
                return await swagger_home(request)
                
            return StarletteFileResponse(os.path.join(SWAGGER_PATH, path))

        self.app.add_route(path="/{0}".format(SWAGGER_URL), route=swagger_home, methods=['GET'], name="swagger_home")
        self.app.add_route(path="/%s/{path:path}" % (SWAGGER_URL), route=swagger_endpoint, methods=['GET'], name="swagger_home_path")
    
    def run(self, host='127.0.0.1', port=8080, bind=None,
            cors=False, cors_allow_origins:list=["*"], gunicorn=True,
            debug=False, workers=1, timeout=200, keepalive=3,
            max_requests=0, threads=1, worker_class='uvicorn.workers.UvicornWorker', ngrok=False, model_id=None, **kwargs):
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
        :cors_allow_origins: Allow hosts of cors
        :gunicorn: Starlette only run with gunicorn = True
        :debug: Debug or not
        :timeout: Timeout of each request
        :keepalive: The number of seconds to wait for requests on a Keep-Alive connection.
        :threads: The number of worker threads for handling requests. Be careful, threads would break your result if it is bigger than 1
        :worker_class: The type of workers to use.
        :max_requests: Max Request to restart Gunicorn Server, default is 0 which means no restart
        :kwargs: Other Gunicorn options
        """
        if not ((sys.version_info.major == 3 and sys.version_info.minor >= 7)
                or sys.version_info.major > 3):
            raise Exception("Starlette must be use with Python 3.7 or higher")

        if not isinstance(bind, list) and not isinstance(bind, str) and bind is not None:
            raise AssertionError(
                "Bind have to be list or string of the form: HOST, HOST:PORT, unix:PATH, fd://FD. An IP is a valid HOST.")

        if debug:
            self.app._debug = debug
        if cors:
            self.app.add_middleware(CORSMiddleware, allow_origins=cors_allow_origins)

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

        # Process bind, host, port
        if isinstance(bind, str):
            bind = [bind]

        bind_host_port = '%s:%s' % (host, port)
        if bind is None:
            bind = [bind_host_port]
        else:
            bind.append(bind_host_port)

        worker_class = 'uvicorn.workers.UvicornWorker'
        logger.info("-" * 80)
        logger.info("Served model with Starlette and Gunicorn at bind={}".format(bind))
        logger.info("Number of workers: {}".format(workers))
        logger.info("Number of threads: {}".format(threads))
        logger.info("API timeout: {}".format(timeout))
        logger.info("Debug = {}".format(debug))
        logger.info("-" * 80)

        loglevel = kwargs.get('loglevel', 'warning' if debug else 'info')
        GunicornWrapper(self.app, bind=bind, workers=workers, timeout=timeout,
                        keepalive=keepalive, max_requests=max_requests,
                        loglevel=loglevel, threads=threads,
                        worker_class=worker_class, **kwargs).run()
