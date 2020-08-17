from .base import MLClient, BaseFunction
import grpc
from ..server.protos import mlchain_pb2_grpc, mlchain_pb2
from mlchain.storage import Path
from mlchain.base.log import logger

class GrpcClient(MLClient):
    def __init__(self, api_key=None, api_address=None, serializer='msgpack', image_encoder=None, name=None,
                 version='lastest', check_status=False, **kwargs):
        MLClient.__init__(self, api_key=api_key, api_address=api_address, serializer=serializer,
                          image_encoder=image_encoder, name=name,
                          version=version, check_status=check_status, **kwargs)
        self.channel = grpc.insecure_channel(api_address)
        self.stub = mlchain_pb2_grpc.MLChainServiceStub(self.channel)
        try:
            ping = self.get('ping')
            logger.info("Connect to server: {0}".format(ping))
        except Exception as e:
            logger.info("Can't connect to server: {0}".format(e))

    def _get(self, api_name, headers=None, params=None):
        """
        GET data from url
        """
        pass

    def _post(self, function_name, headers=None, args=None, kwargs=None):
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        if headers is None:
            headers = {}
        args = [open(arg, 'rb').read() if isinstance(arg, Path) else arg for arg in args]
        kwargs = {k: open(arg, 'rb').read() if isinstance(arg, Path) else arg for k, arg in kwargs.items()}
        header = mlchain_pb2.Header(serializer=self.serializer_type)
        output = self.stub.call(mlchain_pb2.Message(header=header, function_name=function_name,
                                                    args=self.serializer.encode(args),
                                                    kwargs=self.serializer.encode(kwargs),headers = headers))

        return output.output
