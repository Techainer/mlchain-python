```
class Client(ClientBase):
    """
    Mlchain Client Class
    """
    def __init__(self, api_address = None, serializer='json')
```

### Variables:

- api_address (str): Website URL where the current ML model is hosted

- serializer (str): 'json' or 'msgpack' package types where the ML model data is returned