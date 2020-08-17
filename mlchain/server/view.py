from typing import *
from .format import BaseFormat, MLchainFormat
from uuid import uuid4
from mlchain import mlchain_context
import time
from .base import RawResponse, FileResponse, JsonResponse, TemplateResponse, MLChainResponse
from .authentication import Authentication


class View:
    def __init__(self, server, format: BaseFormat = None, authentication: Authentication = None):
        self.server = server
        self.base_format = BaseFormat()
        self.mlchain_format = MLchainFormat()
        self.formats = [self.mlchain_format]
        if isinstance(format, BaseFormat):
            self.formats.insert(0, format)
        self.authentication = authentication

    def parse_data(self):
        raise NotImplementedError

    def make_response(self, response: Union[RawResponse, FileResponse]):
        raise NotImplementedError

    def get_format(self, headers, form, files, data):

        format = self.base_format
        for fm in self.formats:
            if fm.check(headers, form, files, data):
                format = fm
                break
        return format

    def init_context(self, headers):
        context = {key[len('mlchain_context_'):]: value for (key, value) in headers.items() if
                   key.startswith('mlchain_context_')}
        id = uuid4().hex
        mlchain_context.set(context)
        mlchain_context['context_id'] = id
        return id

    def normalize_output(self, format, function_name, headers, output, exception, request_context):
        if isinstance(output, FileResponse):
            output.headers['response-type'] = 'mlchain/file'
        elif isinstance(output, JsonResponse):
            output.headers['response-type'] = 'mlchain/json'
        elif isinstance(output, RawResponse):
            output.headers['response-type'] = 'mlchain/raw'
        elif isinstance(output, MLChainResponse):
            pass
        else:
            output = format.make_response(function_name, headers, output,
                                          exception=exception, request_context=request_context)
        return output

    def __call__(self, function_name, **kws):
        request_context = {
            'api_version': self.server.version
        }
        try:
            headers, form, files, data = self.parse_data()
        except Exception as ex:
            request_context['time_process'] = 0
            output = self.normalize_output(self.base_format, function_name, {}, None, ex, request_context)
            return self.make_response(output)

        format = self.get_format(headers, form, files, data)
        start_time = time.time()
        try:
            if self.authentication is not None:
                self.authentication.check(headers)
            args, kwargs = format.parse_request(function_name, headers, form, files, data, request_context)
            func = self.server.model.get_function(function_name)
            kwargs = self.server.get_kwargs(func, *args, **kwargs)
            kwargs = self.server._normalize_kwargs_to_valid_format(kwargs, func)

            id = self.init_context(headers)
            output = self.server.model.call_function(function_name, id, **kwargs)
            exception = None
        except Exception as ex:
            exception = ex
            output = None
        time_process = time.time() - start_time
        request_context['time_process'] = time_process
        output = self.normalize_output(format, function_name, headers, output, exception, request_context)
        return self.make_response(output)


class ViewAsync(View):
    def __init__(self, server, format=None, authentication: Authentication = None):
        View.__init__(self, server, format, authentication)

    async def parse_data(self):
        return super().parse_data()

    async def make_response(self, response: Union[RawResponse, FileResponse]):
        return super().make_response(response)

    async def __call__(self, function_name, **kws):
        request_context = {
            'api_version': self.server.version
        }
        try:
            headers, form, files, data = await self.parse_data()
        except Exception as ex:
            request_context['time_process'] = 0
            output = self.normalize_output(self.base_format, function_name, {}, None, ex, request_context)
            return await self.make_response(output)
        format = self.get_format(headers, form, files, data)
        start_time = time.time()
        try:
            if self.authentication is not None:
                self.authentication.check(headers)
            args, kwargs = format.parse_request(function_name, headers, form, files, data, request_context)
            func = self.server.model.get_function(function_name)
            kwargs = self.server.get_kwargs(func, *args, **kwargs)
            kwargs = self.server._normalize_kwargs_to_valid_format(kwargs, func)
            id = self.init_context(headers)
            output = await self.server.model.call_async_function(function_name, id, **kwargs)
            exception = None
        except Exception as ex:
            exception = ex
            output = None
        time_process = time.time() - start_time
        request_context['time_process'] = time_process
        output = self.normalize_output(format, function_name, headers, output, exception, request_context)
        return await self.make_response(output)
