import os
import warnings
from inspect import signature, _empty
from collections import defaultdict
from fuzzywuzzy.fuzz import ratio
from mlchain.base import ServeModel
from mlchain.base.serializer import JsonSerializer, MsgpackSerializer, MsgpackBloscSerializer
from mlchain.base.converter import Converter
from mlchain.base.exceptions import MLChainAssertionError
import numpy as np 

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

    def __init__(self, model: ServeModel, name=None):
        if not isinstance(model, ServeModel):
            model = ServeModel(model)
        self.model = model
        self.name = name or model.name
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

    def _initalize_app(self):
        """
        Initalize all endpoint of server
        """

        self._add_endpoint('/api/get_params_<function_name>',
                           '_get_parameters_of_func',
                           handler=self.model._get_parameters_of_func, methods=['GET'])
        self._add_endpoint('/api/des_func_<function_name>',
                           '_get_description_of_func',
                           handler=self.model._get_description_of_func, methods=['GET'])
        self._add_endpoint('/api/ping',
                           '_check_status',
                           handler=self._check_status, methods=['GET'])
        self._add_endpoint('/api/description',
                           '_get_all_description',
                           handler=self.model._get_all_description, methods=['GET'])
        self._add_endpoint('/api/list_all_function',
                           '_list_all_function',
                           handler=self.model._list_all_function, methods=['GET'])
        self._add_endpoint('/api/list_all_function_and_description',
                           '_list_all_function_and_description',
                           handler=self.model._list_all_function_and_description, methods=['GET'])

    def convert(self, value, out_type):
        return self.converter.convert(value, out_type)

    def _normalize_kwargs_to_valid_format(self, kwargs, func_):
        """
        Normalize data into right formats of func_
        """
        inspect_func_ = signature(func_)

        accept_kwargs = "**" in str(inspect_func_)

        # Check valid parameters
        for key, value in list(kwargs.items()):
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
