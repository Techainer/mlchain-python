import time
from typing import Union
from uuid import uuid4
from mlchain import mlchain_context,logger
from mlchain.base.exceptions import MlChainError
from .format import BaseFormat, MLchainFormat, AsyncMLchainFormat
from .base import RawResponse, FileResponse, JsonResponse, MLChainResponse
from flask import Response as FlaskResponse 
from starlette.responses import Response as StarletteResponse
from .authentication import Authentication
import traceback
from sentry_sdk import push_scope, start_transaction
from mlchain import mlconfig
import inspect
from starlette.requests import Request

class View:
    def __init__(self, server, formatter: BaseFormat = None,
                 authentication: Authentication = None):
        self.server = server
        self.base_format = BaseFormat()
        self.mlchain_format = MLchainFormat()
        self.formats = [self.mlchain_format]
        if isinstance(formatter, BaseFormat):
            self.formats.insert(0, formatter)
        self.authentication = authentication

    def parse_data(self):
        raise NotImplementedError

    def make_response(self, response: Union[RawResponse, FileResponse]):
        raise NotImplementedError

    def get_format(self, headers, form, files, data):

        formatter = self.base_format
        for fmt in self.formats:
            if fmt.check(headers, form, files, data):
                formatter = fmt
                break
        return formatter

    def init_context_with_headers(self, headers, context_id:str = None):
        context = {key: value
                   for (key, value) in headers.items()}
        new_context = {}
        for key, value in context.items(): 
            if key.lower().startswith("mlchain-context") or key.lower().startswith("mlchain_context"): 
                new_context[key.upper().replace("-", "_")] = value
        context.update(new_context)

        mlchain_context.set(context)

        if mlchain_context.MLCHAIN_CONTEXT_ID is None: 
            mlchain_context['MLCHAIN_CONTEXT_ID'] = context_id 
        else: 
            context_id = mlchain_context['MLCHAIN_CONTEXT_ID']
            
        return context_id

    def init_context(self): 
        uid = str(uuid4())
        mlchain_context['MLCHAIN_CONTEXT_ID'] = uid
        return uid 
        
    def normalize_output(self, formatter, function_name, headers,
                         output, exception, request_context):
        if isinstance(output, FileResponse):
            output.headers['response-type'] = 'mlchain/file'
        elif isinstance(output, JsonResponse):
            output.headers['response-type'] = 'mlchain/json'
        elif isinstance(output, RawResponse):
            output.headers['response-type'] = 'mlchain/raw'
        elif isinstance(output, FlaskResponse):
            output.headers['response-type'] = 'mlchain/flask_raw'
        elif isinstance(output, StarletteResponse):
            output.headers['response-type'] = 'mlchain/starlette_raw'
        elif isinstance(output, MLChainResponse):
            pass
        else:
            output = formatter.make_response(function_name, headers, output,
                                             exception=exception,
                                             request_context=request_context)
        return output

    def __call__(self, *args, **kwargs): 
        if "function_name" in kwargs: 
            function_name = kwargs.pop('function_name')
        else: 
            function_name = args[0]

        return self.call_function(function_name=function_name, **kwargs)

    def call_function(self, function_name, **kws):
        with push_scope() as sentry_scope:
            transaction_name = "{0}  ||  {1}".format(mlconfig.MLCHAIN_SERVER_NAME, function_name)
            sentry_scope.transaction = transaction_name
            
            with start_transaction(op="task", name=transaction_name):
                uid = self.init_context()

                request_context = {
                    'api_version': self.server.version
                }
                try:
                    headers, form, files, data = self.parse_data()
                except Exception as ex:
                    request_context['time_process'] = 0
                    output = self.normalize_output(self.base_format, function_name, {},
                                                None, ex, request_context)
                    return self.make_response(output)

                formatter = self.get_format(headers, form, files, data)
                start_time = time.time()
                try:
                    if self.authentication is not None:
                        self.authentication.check(headers)
                    args, kwargs = formatter.parse_request(function_name, headers, form,
                                                        files, data, request_context)
                    func = self.server.model.get_function(function_name)
                    kwargs = self.server.get_kwargs(func, *args, **kwargs)
                    kwargs = self.server._normalize_kwargs_to_valid_format(kwargs, func)

                    uid = self.init_context_with_headers(headers, uid)
                    sentry_scope.set_tag("transaction_id", uid)
                    logger.debug("Mlchain transaction id: {0}".format(uid))

                    output = self.server.model.call_function(function_name, uid, **kwargs)
                    exception = None
                except MlChainError as ex:
                    exception = ex
                    output = None
                except Exception as ex:
                    exception = ex
                    output = None

                time_process = time.time() - start_time
                request_context['time_process'] = time_process
                output = self.normalize_output(formatter, function_name, headers,
                                            output, exception, request_context)
                return self.make_response(output)


class StarletteAsyncView(View):
    def __init__(self, server, formatter=None, authentication: Authentication = None):
        View.__init__(self, server, formatter, authentication)

        self.mlchain_format = AsyncMLchainFormat()
        self.formats = [self.mlchain_format]
        if isinstance(formatter, BaseFormat):
            self.formats.insert(0, formatter)

    async def parse_data(self):
        return super().parse_data()

    async def make_response(self, response: Union[RawResponse, FileResponse]):
        return super().make_response(response)

    async def __call__(self, scope, receive, send, *args, **kwargs): 
        request = Request(scope, receive)
        function_name = request.path_params['function_name']
        return await self.call_function(function_name, request, scope, receive, send, **kwargs)
        
    async def call_function(self, function_name, request, scope, receive, send, **kws):
        function_name = function_name.strip("/")
        with push_scope() as sentry_scope:
            transaction_name = "{0}  ||  {1}".format(mlconfig.MLCHAIN_SERVER_NAME, function_name)
            sentry_scope.transaction = transaction_name
            
            with start_transaction(op="task", name=transaction_name):
                uid = self.init_context()

                request_context = {
                    'api_version': self.server.version
                }
                try:
                    headers, form, files, data = await self.parse_data(request)
                except Exception as ex:
                    request_context['time_process'] = 0
                    output = self.normalize_output(self.base_format, function_name, {},
                                                None, ex, request_context)
                    return await self.make_response(output, request, scope, receive, send)
                formatter = self.get_format(headers, form, files, data)
                start_time = time.time()
                try:
                    if self.authentication is not None:
                        self.authentication.check(headers)
                    
                    if inspect.iscoroutinefunction(formatter.parse_request):
                        args, kwargs = await formatter.parse_request(function_name, headers, form,
                                                            files, data, request_context)
                    else:
                        args, kwargs = formatter.parse_request(function_name, headers, form,
                                                            files, data, request_context)
                    func = self.server.model.get_function(function_name)
                    kwargs = self.server.get_kwargs(func, *args, **kwargs)
                    kwargs = await self.server._normalize_kwargs_to_valid_format(kwargs, func)
                    uid = self.init_context_with_headers(headers, uid)
                    sentry_scope.set_tag("transaction_id", uid)
                    logger.debug("Mlchain transaction id: {0}".format(uid))

                    output = await self.server.model.call_async_function(function_name, uid, **kwargs)
                    exception = None
                except MlChainError as ex:
                    exception = ex
                    output = None
                except Exception as ex:
                    exception = ex
                    output = None

                time_process = time.time() - start_time
                request_context['time_process'] = time_process
                output = self.normalize_output(formatter, function_name, headers,
                                            output, exception, request_context)
                return await self.make_response(output, request, scope, receive, send)
