import os
import time
import mlchain
from mlchain import mlchain_context
from mlchain.base.serializer import (JsonSerializer, MsgpackSerializer,
                                     MsgpackBloscSerializer, JpgMsgpackSerializer, PngMsgpackSerializer, Serializer)
from mlchain.base.log import except_handler, logger
from mlchain.server.base import RawResponse
from sentry_sdk import Hub
from httpx import (
    ConnectError,
    ReadTimeout,
    WriteTimeout,
)
from mlchain.base.exceptions import MLChainConnectionError, MLChainTimeoutError

class AsyncStorage:
    def __init__(self, function):
        self.function = function

    def get(self, key):
        return AsyncResult(self.function(key))

    def get_wait_until_done(self, key, timeout=100, interval=0.5):
        start = time.time()
        result = AsyncResult(self.function(key))
        while not (result.is_success() or time.time() - start > timeout):
            time.sleep(interval)
            result = AsyncResult(self.function(key))
        return result


class AsyncResult:
    def __init__(self, response):
        self.response = response

    @property
    def output(self):
        if 'output' in self.response:
            return self.response['output']
        return None

    @property
    def status(self):
        if 'status' in self.response:
            return self.response['status']
        return None

    @property
    def time(self):
        if 'time' in self.response:
            return self.response['time']
        return 0

    def is_success(self):
        if self.status == 'SUCCESS':
            return True
        return False

    def json(self):
        return self.response


class MLClient:
    def __init__(self, api_key=None, api_address=None, serializer='msgpack',
                 image_encoder=None, timeout=5 * 60,
                 name=None, version='lastest',
                 check_status=False, headers={}, **kwargs):
        """
        Client to communicate with Mlchain server
        :api_key: Your API KEY
        :api_address: API or URL of server to communicate with
        :serializer: The way to serialize data ['json', 'msgpack', 'msgpack_blosc']
        """
        assert serializer in ['json', 'msgpack', 'msgpack_blosc']
        assert image_encoder in ['jpg', 'png', None]

        if api_key is None and os.getenv('MLCHAIN_API_KEY') is not None:
            api_key = os.getenv('MLCHAIN_API_KEY')
        self.api_key = api_key
        self.name = name
        self.version = version
        self.chek_status = check_status
        if api_address is None:
            if os.getenv('MLCHAIN_API_ADDRESS') is not None:
                api_address = os.getenv('MLCHAIN_API_ADDRESS')
            else:
                api_address = mlchain.API_ADDRESS
        self.api_address = api_address
        if isinstance(headers, dict):
            self.headers = headers
        else:
            raise AssertionError("{} headers is invalid. Only allow dictionary header.".format(type(headers)))
        self.json_serializer = JsonSerializer()

        # Serializer initalization
        self.serializer_type = serializer
        try:
            if serializer == 'msgpack':
                if image_encoder is None:
                    self.serializer = MsgpackSerializer()
                elif image_encoder == 'jpg':
                    self.serializer = JpgMsgpackSerializer()
                elif image_encoder == 'png':
                    self.serializer = PngMsgpackSerializer()
            elif serializer == 'msgpack_blosc':
                self.serializer = MsgpackBloscSerializer()
            else:
                self.serializer_type = 'json'
                self.serializer = self.json_serializer
        except:
            logger.info("{0} not found, using json instead".format(serializer))
            self.serializer_type = 'json'
            self.serializer = self.json_serializer

        self.image_encoder = image_encoder
        self._cache = {}
        self.store_ = None
        self.all_func_des = None
        self.all_func_params = None
        self.all_attributes = None
        self.timeout = timeout

    def _get_function(self, name):
        return BaseFunction(client=self, function_name=name,
                            serializer=self.serializer)

    @property
    def store(self):
        if self.store_ is None:
            self.store_ = AsyncStorage(self._get_function('store_get'))
        return self.store_

    def __check_function(self, name):
        if self.all_func_des is not None:
            if name in self.all_func_des:
                return True
            return False
        return True

    def __check_attribute(self, name):
        if self.all_attributes is not None:
            if name in self.all_attributes:
                return True
            return False
        return True

    def __getattr__(self, name):
        if name in self._cache:
            return self._cache[name]

        if not self.__check_function(name):
            if not self.__check_attribute(name) and not name.endswith('_async'):
                raise AssertionError("This model has no method or attribute name = {0} or it hasnt been served. The only served is: \n\
                                        Functions: {1} \n\
                                        Attributes: {2}".format(name,
                                                                list(self.all_func_des.keys()),
                                                                list(self.all_attributes)))
            return self._get_function(name=name)()

        true_function = self._get_function(name=name)
        self._cache[name] = true_function
        return true_function

    def _post(self, function_name, headers=None, args=None, kwargs=None):
        raise NotImplementedError

    def post(self, function_name, headers=None, args=None, kwargs=None):
        def _call_post(): 
            context = {key: value
                    for (key, value) in mlchain_context.items() if key.startswith('MLCHAIN_CONTEXT_')}
            context.update(**self.headers)

            output = None
            try:
                output = self._post(function_name, context, args, kwargs)
            except ConnectError: 
                raise MLChainConnectionError(msg="Client call can not connect into Server: {0}. Function: {1}. POST".format(self.api_address, function_name))
            except TimeoutError: 
                raise MLChainTimeoutError(msg="Client call timeout into Server: {0}. Function: {1}. POST".format(self.api_address, function_name))
            except ReadTimeout: 
                raise MLChainTimeoutError(msg="Client call timeout into Server: {0}. Function: {1}. POST".format(self.api_address, function_name))
            except WriteTimeout: 
                raise MLChainTimeoutError(msg="Client call timeout into Server: {0}. Function: {1}. POST".format(self.api_address, function_name))

            return output

        transaction = Hub.current.scope.transaction

        if transaction is not None:
            with transaction.start_child(op="task", description="{0} {1}".format(self.api_address, function_name)) as span:
                return _call_post()
        else: 
            return _call_post()

    def _get(self, api_name, headers=None, timeout=None):
        raise NotImplementedError

    def get(self, api_name, headers=None, timeout=None):
        def _call_get(): 
            context = {key: value
                        for (key, value) in mlchain_context.items() if key.startswith('MLCHAIN_CONTEXT_')}
            context.update(**self.headers)

            output = None
            try:
                output = self._get(api_name, self.headers, timeout)
            except ConnectError: 
                raise MLChainConnectionError(msg="Client call can not connect into Server: {0}. Function: {1}. GET".format(self.api_address, api_name))
            except TimeoutError: 
                raise MLChainTimeoutError(msg="Client call timeout into Server: {0}. Function: {1}. GET".format(self.api_address, api_name))
            except ReadTimeout: 
                raise MLChainTimeoutError(msg="Client call timeout into Server: {0}. Function: {1}. GET".format(self.api_address, api_name))
            except WriteTimeout: 
                raise MLChainTimeoutError(msg="Client call timeout into Server: {0}. Function: {1}. GET".format(self.api_address, api_name))

            return output

        transaction = Hub.current.scope.transaction

        if transaction is not None:
            with transaction.start_child(op="task", description="{0} {1}".format(self.api_address, api_name)) as span:
                return _call_get()
        else: 
            return _call_get()

class BaseFunction:
    def __init__(self, client, function_name, serializer: Serializer):
        self.client = client
        self.function_name = function_name
        self.serializer = serializer

    @property
    def headers(self):
        return {}

    def __call__(self, *args, **kwargs):
        output = self.client.post(function_name=self.function_name, args=args, kwargs=kwargs)
        if isinstance(output, RawResponse):
            return output.value
        output = self.serializer.decode(output)
        if 'error' in output:
            with except_handler():
                raise Exception(
                    "MLCHAIN VERSION: {} \n API VERSION: {} \n ERROR_CODE: {} \n INFO_ERROR: {}, ".format(
                        output.get('mlchain_version', None), output.get('api_version', None),
                        output.get('code', None), output['error']))

        return output['output']
