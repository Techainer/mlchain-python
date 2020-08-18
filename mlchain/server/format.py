from typing import List, Tuple, Dict
import traceback
from mlchain import logger, __version__
from mlchain.base.serializer import JsonSerializer, MsgpackSerializer, MsgpackBloscSerializer
from mlchain.base.exceptions import MLChainSerializationError, MlChainError
from .base import RawResponse, JsonResponse, MLChainResponse


class BaseFormat:
    def check(self, headers, form, files, data) -> bool:
        return False

    def parse_request(self, function_name, headers, form,
                      files, data, request_context) -> Tuple[List, Dict]:
        kwargs = form
        for k, v in files.items():
            if k in kwargs:
                kwargs[k].extend(v)
            else:
                kwargs[k] = v
        if '__args__' in kwargs:
            args = kwargs.pop('__args__')
        else:
            args = []

        kwargs = {k: v if len(v) > 1 else v[0] for k, v in kwargs.items()}
        return args, kwargs

    def make_response(self, function_name, headers,
                      output, request_context, exception=None) -> MLChainResponse:
        if exception is None:
            if isinstance(output, MLChainResponse):
                return output
            output = {
                'output': output,
                'time': request_context.get('time_process'),
                'api_version': request_context.get('api_version'),
                'mlchain_version': __version__
            }
            return JsonResponse(output, 200)
        else:
            if isinstance(exception, MlChainError):
                output = {
                    'error': exception.msg,
                    'code': exception.code,
                    'api_version': request_context.get('api_version'),
                    'mlchain_version': __version__
                }
                return JsonResponse(output, exception.status_code)
            if isinstance(exception, Exception):
                error = ''.join(traceback.extract_tb(exception.__traceback__).format()).strip()
                output = {
                    'error': error,
                    'api_version': request_context.get('api_version'),
                    'mlchain_version': __version__
                }
                return JsonResponse(output, 500)
            output = {
                'error': str(exception),
                'api_version': request_context.get('api_version'),
                'mlchain_version': __version__
            }
            return JsonResponse(output, 500)


class MLchainFormat(BaseFormat):
    def __init__(self):
        self.serializers = {}
        for name, cls in [('json', JsonSerializer),
                          ('msgpack', MsgpackSerializer),
                          ('msgpack_blosc', MsgpackBloscSerializer)]:
            try:
                serializer = cls()
                self.serializers[name] = serializer
            except Exception as ex:
                logger.warn("Can't load {0} with error: {1}".format(cls.__name__, ex))

    def check(self, headers, form, files, data):
        if '__parameters__' in files and 'mlchain-serializer' in headers:
            return True
        return False

    def parse_request(self, function_name, headers, form,
                      files, data, request_context):
        parameters = files['__parameters__'][0].read()
        serializer_type = headers.get('mlchain-serializer', 'json')
        serializer = self.serializers.get(serializer_type, None)
        if serializer is None:
            raise MLChainSerializationError("Not found serializer {0}".format(serializer_type))
        args, kwargs = serializer.decode(parameters)

        for idx, value in enumerate(args):
            if isinstance(value, str) and value.startswith('__file__') \
                    and value in files:
                args[idx] = files[value][0].read()

        for key, value in kwargs.items():
            if isinstance(value, str) and value.startswith('__file__') \
                    and value in files:
                kwargs[key] = files[value][0].read()
        return args, kwargs

    def make_response(self, function_name, headers, output,
                      request_context, exception=None):
        if exception is None:
            output = {
                'output': output,
                'time': request_context.get('time_process'),
                'api_version': request_context.get('api_version'),
                'mlchain_version': __version__
            }
            status = 200
        else:
            if isinstance(exception, MlChainError):
                output = {
                    'error': exception.msg,
                    'code': exception.code,
                    'api_version': request_context.get('api_version'),
                    'mlchain_version': __version__
                }
                status = exception.status_code

            elif isinstance(exception, Exception):
                error = ''.join(traceback.extract_tb(exception.__traceback__).format()).strip()
                output = {
                    'error': error,
                    'api_version': request_context.get('api_version'),
                    'mlchain_version': __version__
                }
                status = 500
            else:
                output = {
                    'error': str(exception),
                    'api_version': request_context.get('api_version'),
                    'mlchain_version': __version__
                }
                status = 500

        serializer_type = headers.get('mlchain-serializer', 'json')
        serializer = self.serializers.get(serializer_type, None)
        if serializer is None:
            raise MLChainSerializationError("Not found serializer {0}".format(serializer_type))

        response = serializer.encode(output)
        content_type = 'application/{0}'.format(serializer_type)
        return RawResponse(response=response, status=status,
                           headers={'Content-type': content_type})


class RawFormat(BaseFormat):
    def check(self, headers, form, files, data):
        return True

    def make_response(self, function_name, headers, output,
                      request_context, exception=None):
        if exception is None:
            return JsonResponse(output, 200)
        return super().make_response(function_name, headers,
                                     output, request_context, exception)
