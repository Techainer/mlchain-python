from mlchain import mlconfig
from mlchain.base import logger
from .http_client import HttpClient

class Client(HttpClient):
    def __init__(self, api_key=None, api_address=None, serializer='json', timeout=5 * 60, headers={},
                 name: str = "", version: str = "", check_status=False):
        self._api_key = api_key
        self._api_address = api_address
        self._serializer = serializer
        self._timeout = timeout
        self._headers = headers
        HttpClient.__init__(self, api_key=api_key, api_address=api_address, serializer=serializer,
                            timeout=timeout, headers=headers, name=name, version=version,
                            check_status=check_status)

    def model(self, name: str = "", version: str = "", check_status=False):
        return HttpClient(api_key=self._api_key, api_address=self._api_address, serializer=self._serializer,
                            timeout=self._timeout, headers=self._headers, name=name, version=version,
                            check_status=check_status)

def get_model(name):
    config = mlconfig.get_client_config(name)
    timeout = config.timeout
    if timeout is not None:
        try:
            timeout = int(timeout)
        except:
            raise ValueError("timeout must be an integer")
    client_type = mlconfig.type or 'http'
    if config.ckeck_status is None:
        check_status = False
    elif isinstance(config.check_status, str) and config.check_status.lower() in ['y', 'yes', 'true', 't']:
        check_status = True
    elif isinstance(config.check_status, (int, float)) and config.check_status > 0:
        check_status = True
    else:
        check_status = False
    return Client(api_key=config.api_key, api_address=config.api_address,
                  serializer=config.serializer or 'json', timeout=timeout, type=client_type, check_status=check_status)
