from mlchain.base.serve_model import ServeModel
from concurrent import futures
from .base import MLServer
import grpc
from .protos import mlchain_pb2, mlchain_pb2_grpc
from threading import Thread
import time
import mlchain
from mlchain import mlchain_context
from uuid import uuid4
from mlchain.base.exceptions import MlChainError
from mlchain.base.log import logger


class GrpcServer(mlchain_pb2_grpc.MLChainServiceServicer, MLServer):
    """Provides methods that implement functionality of route guide server."""

    def __init__(self, model: ServeModel, name=None, api_keys=None, version='0.0'):
        MLServer.__init__(self, model, name=name)
        self.version = version

    def get_serializer(self, serializer):
        if serializer in self.serializers_dict:
            return self.serializers_dict[serializer]
        else:
            return self.serializers_dict['application/json']

    def ping(self, request, context):
        return mlchain_pb2.Byte(value=b'pong')

    def call(self, request, context):
        header = request.header
        function_name = request.function_name
        args = request.args
        kwargs = request.kwargs
        serializer = self.get_serializer(header.serializer)
        headers = request.headers
        id = uuid4().hex
        mlchain_context.set(headers)
        mlchain_context['context_id'] = id
        args = serializer.decode(args)
        kwargs = serializer.decode(kwargs)
        func = self.model.get_function(function_name)
        kwargs = self.get_kwargs(func, *args, **kwargs)
        kwargs = self._normalize_kwargs_to_valid_format(kwargs, func)
        try:
            start = time.time()
            output = self.model.call_function(function_name, None, **kwargs)
            duration = time.time() - start
            output = {
                'output': output,
                'time': duration,
                'api_version': self.version,
                'mlchain_version': mlchain.__version__
            }
        except MlChainError as ex:
            err = ex.msg
            logger.error("code: {0} msg: {1}".format(ex.code, ex.msg))
            output = {
                'error': err,
                'time': 0,
                'code': ex.code,
                'api_version': self.version,
                'mlchain_version': mlchain.__version__
            }

        except Exception as ex:
            output = {
                'output': str(ex),
                'time': 0,
                'api_version': self.version,
                'mlchain_version': mlchain.__version__
            }
        return mlchain_pb2.Output(output=serializer.encode(output))

    def run(self, host='127.0.0.1', port=10010, workers=1, block=True):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=workers))
        mlchain_pb2_grpc.add_MLChainServiceServicer_to_server(self, server)
        server.add_insecure_port('{0}:{1}'.format(host, port))
        server.start()
        if block:
            server.wait_for_termination()
        else:
            Thread(target=server.wait_for_termination).start()
