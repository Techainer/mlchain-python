import os
from mlchain.base.exceptions import MLChainUnauthorized


class Authentication:
    def __init__(self, api_keys=None):
        api_keys = api_keys or os.getenv('API_KEYS', None)
        if isinstance(api_keys, str):
            api_keys = api_keys.split(';')
        self.api_keys = api_keys

    def check(self, headers):
        if self.api_keys is not None or (isinstance(self.api_keys, (list, dict))
                                         and len(self.api_keys) > 0):
            authorized = False
            has_key = False
            for key in ['x-api-key', 'apikey', 'apiKey', 'api-key']:
                apikey = headers.get(key, '')
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
                raise MLChainUnauthorized(error)
        return True
