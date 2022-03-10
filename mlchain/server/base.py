import os
import importlib
import warnings
from inspect import signature, _empty
from collections import defaultdict
from thefuzz.fuzz import ratio
from mlchain.base import ServeModel
from mlchain.base.log import logger
from mlchain.base.serializer import JsonSerializer, MsgpackSerializer, MsgpackBloscSerializer
from mlchain.base.converter import Converter, AsyncConverter
from mlchain.base.exceptions import MLChainAssertionError
import numpy as np 
from mlchain import mlchain_context

class MLChainResponse:
    '''
    Base class custom response
    '''


class RawResponse(MLChainResponse):
    def __init__(self, response=None,
                 status=None,
                 headers=None,
                 mimetype=None,
                 content_type=None):
        self.value = response
        self.response = response
        self.status = status
        if headers is None:
            headers = {}
        self.headers = headers
        self.mimetype = mimetype
        self.content_type = content_type


class JsonResponse(RawResponse):
    serializer = JsonSerializer()

    def __init__(self, data, status=None, headers=None):
        RawResponse.__init__(self, self.serializer.encode(data), status=status,
                             headers=headers,
                             content_type='application/json')
        self.value = data


class FileResponse(MLChainResponse):
    def __init__(self, path, mimetype=None, headers=None):
        assert os.path.exists(path), "File not found. {0}".format(path)
        self.path = path
        self.mimetype = mimetype
        if headers is None:
            headers = {}
        self.headers = headers


class TemplateResponse(MLChainResponse):
    def __init__(self, template_name, **context):
        self.template_name = template_name
        self.context = context


class MLServer:
    convert_dict = defaultdict(dict)
    file_converters = {}

    def __init__(self, model: ServeModel, name=None, version=None, api_format=None, authentication=None):
        if not isinstance(model, ServeModel):
            model = ServeModel(model)
        self.model = model
        self.name = name or model.name
        self.version = version
        self.api_format = api_format
        self.authentication = authentication

        self.serializers_dict = {
            'application/json': JsonSerializer(),
            'application/msgpack': MsgpackSerializer(),
        }
        try:
            self.serializers_dict['application/msgpack_blosc'] = MsgpackBloscSerializer()
        except:
            self.serializers_dict['application/msgpack_blosc'] = self.serializers_dict['application/msgpack']
            warnings.warn("Can't load MsgpackBloscSerializer. Use msgpack instead")
        self.converter = Converter()

        self.initialize_app()
        
    def _check_status(self):
        """
        Check status of a served model
        """
        return "pong"

    def _add_endpoint(self, endpoint=None, endpoint_name=None,
                      handler=None, methods=['GET', 'POST']):
        """
        Add one endpoint to the flask application. Accept GET, POST and PUT.
        :param endpoint: Callable URL.
        :param endpoint_name: Name of the Endpoint
        :param handler: function to execute on call on the URL
        :return: Nothing
        """
        raise NotImplementedError
    
    def _register_swagger(self): 
        """
        Add Swagger to URL
        """
        raise NotImplementedError
    
    def register_swagger(self): 
        """
        Add Swagger to URL
        """
        return self._register_swagger()

    def add_endpoint(self, endpoint=None, endpoint_name=None,
                      handler=None, methods=['GET', 'POST']):
        """
        Add one endpoint to the flask application. Accept GET, POST and PUT.
        :param endpoint: Callable URL.
        :param endpoint_name: Name of the Endpoint
        :param handler: function to execute on call on the URL
        :return: Nothing
        """
        return self._add_endpoint(endpoint=endpoint, endpoint_name=endpoint_name, handler=handler, methods=methods)

    def _initialize_app(self):
        """
        Initialize some components of server
        """
        api_format = self.api_format
        if isinstance(api_format, str):
            try:
                package, class_name = api_format.rsplit('.', 1)
                api_format = importlib.import_module(package)
                api_format = getattr(api_format, class_name)
            except:
                api_format = None
        if isinstance(api_format, type):
            api_format = api_format()

        self.api_format_class = api_format
        self.api_format = '{0}.{1}'.format(api_format.__class__.__module__,
                                           api_format.__class__.__name__)

    def initialize_app(self):
        """
        Initialize some components of server
        """
        return self._initialize_app()

    def initialize_endpoint(self): 
        """
        Initialize Server Endpoint
        """
        self.add_endpoint('/api/get_params/<function_name>',
                           '_get_parameters_of_func',
                           handler=self.model._get_parameters_of_func, methods=['GET'])
        self.add_endpoint('/api/des_func/<function_name>',
                           '_get_description_of_func',
                           handler=self.model._get_description_of_func, methods=['GET'])
        self.add_endpoint('/api/ping',
                           '_check_status',
                           handler=self._check_status, methods=['GET'])
        self.add_endpoint('/api/description',
                           '_get_all_description',
                           handler=self.model._get_all_description, methods=['GET'])
        self.add_endpoint('/api/list_all_function',
                           '_list_all_function',
                           handler=self.model._list_all_function, methods=['GET'])
        self.add_endpoint('/api/list_all_function_and_description',
                           '_list_all_function_and_description',
                           handler=self.model._list_all_function_and_description, methods=['GET'])

        
        self._register_home()

        try:
            self._register_swagger()
        except Exception as ex:
            logger.error("Can't register swagger with error {0}".format(ex))

    def convert(self, value, out_type):
        """
        Convert the value in to out_type
        :value: The value
        :out_type: Expected type
        """
        return self.converter.convert(value, out_type)

    def _normalize_kwargs_to_valid_format(self, kwargs, func_):
        """
        Normalize data into right formats of func_
        """
        inspect_func_ = signature(func_)

        accept_kwargs = "**" in str(inspect_func_)

        # Check valid parameters
        for key, value in list(kwargs.items()):
            mlchain_context['CONVERT_VARIABLE'] = key
            if key in inspect_func_.parameters:
                req_type = inspect_func_.parameters[key].annotation
                the_default = inspect_func_.parameters[key].default

                if type(value) != req_type: 
                    eq = value == the_default
                    
                    if isinstance(eq, np.ndarray): 
                        if not np.all(eq): 
                            kwargs[key] = self.convert(value, req_type)
                    elif not eq: 
                        kwargs[key] = self.convert(value, req_type)
            elif not accept_kwargs:
                suggest = None
                fuzz = 0
                for k in inspect_func_.parameters:
                    if suggest is None:
                        suggest = k
                        fuzz = ratio(k.lower(), key.lower())
                    elif ratio(k.lower(), key.lower()) > fuzz:
                        suggest = k
                        fuzz = ratio(k.lower(), key.lower())
                kwargs.pop(key)

        missing = []
        for key, parameter in inspect_func_.parameters.items():
            if key not in kwargs and parameter.default == _empty:
                missing.append(key)
        if len(missing) > 0:
            raise MLChainAssertionError("Missing params {0}".format(missing))
        return kwargs

    def get_kwargs(self, func, *args, **kwargs):
        sig = signature(func)
        parameters = sig.parameters

        kwgs = {}
        for key, value in zip(parameters.keys(), args):
            kwgs[key] = value
        kwgs.update(kwargs)
        return kwgs

class AsyncMLServer(MLServer):
    async def _normalize_kwargs_to_valid_format(self, kwargs, func_):
        """
        Normalize data into right formats of func_
        """
        inspect_func_ = signature(func_)

        accept_kwargs = "**" in str(inspect_func_)

        # Check valid parameters
        for key, value in list(kwargs.items()):
            mlchain_context['CONVERT_VARIABLE'] = key
            if key in inspect_func_.parameters:
                req_type = inspect_func_.parameters[key].annotation
                the_default = inspect_func_.parameters[key].default

                if type(value) != req_type: 
                    eq = value == the_default
                    
                    if isinstance(eq, np.ndarray): 
                        if not np.all(eq): 
                            kwargs[key] = await self.convert(value, req_type)
                    elif not eq: 
                        kwargs[key] = await self.convert(value, req_type)
            elif not accept_kwargs:
                suggest = None
                fuzz = 0
                for k in inspect_func_.parameters:
                    if suggest is None:
                        suggest = k
                        fuzz = ratio(k.lower(), key.lower())
                    elif ratio(k.lower(), key.lower()) > fuzz:
                        suggest = k
                        fuzz = ratio(k.lower(), key.lower())
                kwargs.pop(key)

        missing = []
        for key, parameter in inspect_func_.parameters.items():
            if key not in kwargs and parameter.default == _empty:
                missing.append(key)
        if len(missing) > 0:
            raise MLChainAssertionError("Missing params {0}".format(missing))
        return kwargs