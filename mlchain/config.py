import os
from os import environ
from collections import defaultdict
from .base.log import logger
import datetime
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import datetime

class BaseConfig(dict):
    def __init__(self, env_key='', **kwargs):
        self.env_key = env_key
        dict.__init__(self)
        self.update_default(kwargs)

    def __getattr__(self, item):
        r = self.get_item(item)
        if r is not None:
            return r

        r = self.get_item(item.upper())
        if r is not None:
            return r

        r = self.get_item(item.lower())
        if r is not None:
            return r

        if item.upper() in self:
            return self[item.upper()]
            
        r = self.get_default(item)
        return r

    def get_item(self, item):
        r = environ.get(item)
        if r is not None:
            return r

        return None 

    def from_json(self, path):
        import json
        self.update(json.load(open(path, encoding='utf-8')))

    def from_yaml(self, path):
        import yaml
        self.update(yaml.load(open(path), Loader=yaml.FullLoader))

    def update(self, data):
        for k, v in data.items():
            self[k.upper()] = v

    def get_default(self, item):
        key = item.upper()
        if not key.endswith('_DEFAULT'):
            key += '_DEFAULT'
        if key in self:
            return self[key]
        return None

    def update_default(self, data):
        for k, v in data.items():
            key = k.upper()
            if not key.endswith('_DEFAULT'):
                key += '_DEFAULT'
            self[key] = v


object_storage_config = BaseConfig(env_key='OBJECT_STORAGE_')


class MLConfig(BaseConfig):
    def __init__(self, *args, **kwargs):
        BaseConfig.__init__(self, *args, **kwargs)
        self.clients = defaultdict(dict)

    def update_client(self, clients):
        self.clients.update({k.upper(): v for k, v in clients.items()})

    def load_config(self, path, mode=None):
        if isinstance(path, str) and os.path.exists(path):
            if path.endswith('.json'):
                data = load_json(path)
            elif path.endswith('.yaml') or path.endswith('.yml'):
                data = load_yaml(path)
            else:
                raise AssertionError("Only support config file is json or yaml")
        else:
            data = path
        if 'clients' in data:
            self.update_client(data['clients'])
        if 'mode' in data:
            if 'default' in data['mode']:
                default = data['mode']['default']
            else:
                default = 'default'
            default = mode or default
            if 'env' in data['mode']:
                for mode in ['default', default]:
                    if mode in data['mode']['env']:
                        for k, v in data['mode']['env'][mode].items():
                            if k in environ:
                                data['mode']['env'][mode][k] = environ[k]
                        self.update(data['mode']['env'][mode])

    def get_client_config(self, name):
        name = name.upper()
        return BaseConfig(env_key='CLIENT_{0}_'.format(name), **self.clients[name])


mlconfig = MLConfig(env_key='')

all_configs = [object_storage_config]


def load_config(data):
    mlconfig.update({
        "MLCHAIN_SERVER_NAME": data.get("name", 'mlchain-server'), 
        "MLCHAIN_SERVER_VERSION": data.get("version", "0.0.1")
    })

    default = 'default'
    if 'mode' in data:
        if 'default' in data['mode']:
            default = data['mode']['default']

    mlconfig.update({
        "MLCHAIN_DEFAULT_MODE": default
    })

    if "sentry" in data: 
        mlconfig.update({
            "MLCHAIN_SENTRY_DSN": os.getenv("SENTRY_DSN", data['sentry'].get("dsn", None)), 
            "MLCHAIN_SENTRY_TRACES_SAMPLE_RATE": os.getenv("SENTRY_TRACES_SAMPLE_RATE", data['sentry'].get("traces_sample_rate", 0.1)), 
            "MLCHAIN_SENTRY_SAMPLE_RATE": os.getenv("SENTRY_SAMPLE_RATE", data['sentry'].get("sample_rate", 1.0)),
            "MLCHAIN_SENTRY_DROP_MODULES": os.getenv("SENTRY_DROP_MODULES", data['sentry'].get("drop_modules", 'True')) not in ['False', 'false', False]
        })

    for config in all_configs:
        env_key = config.env_key.strip('_').lower()
        if env_key in data:
            config.update(data[env_key])
            
    if 'clients' in data:
        mlconfig.update_client(data['clients'])

    if 'mode' in data:
        if 'env' in data['mode']:
            for mode in ['default', default]:
                if mode in data['mode']['env']:
                    for k, v in data['mode']['env'][mode].items():
                        if k in environ:
                            data['mode']['env'][mode][k] = environ[k]
                    mlconfig.update(data['mode']['env'][mode])
    
    if (mlconfig.MLCHAIN_SENTRY_DSN is not None and mlconfig.MLCHAIN_SENTRY_DSN != 'None') and data.get('wrapper', None) != 'gunicorn': 
        init_sentry()

def before_send(event, hint): 
    if mlconfig.MLCHAIN_SENTRY_DROP_MODULES: 
        event['modules'] = {}

    return event

def init_sentry():
    if mlconfig.MLCHAIN_SENTRY_DSN is None or mlconfig.MLCHAIN_SENTRY_DSN == 'None':
        return None
    logger.debug("Initializing Sentry to {0} and traces_sample_rate: {1} and sample_rate: {2} and drop_modules: {3}".format(mlconfig.MLCHAIN_SENTRY_DSN, mlconfig.MLCHAIN_SENTRY_TRACES_SAMPLE_RATE, mlconfig.MLCHAIN_SENTRY_SAMPLE_RATE, mlconfig.MLCHAIN_SENTRY_DROP_MODULES))
    try:
        sentry_sdk.init(
            dsn=mlconfig.MLCHAIN_SENTRY_DSN,
            integrations=[FlaskIntegration()],
            sample_rate=mlconfig.MLCHAIN_SENTRY_SAMPLE_RATE,
            traces_sample_rate=mlconfig.MLCHAIN_SENTRY_TRACES_SAMPLE_RATE,
            server_name=mlconfig.MLCHAIN_SERVER_NAME,
            environment=mlconfig.MLCHAIN_DEFAULT_MODE, 
            before_send=before_send
        )

        sentry_sdk.set_context(
            key = "app", 
            value = {
                "app_start_time": datetime.datetime.now(),
                "app_name": str(mlconfig.MLCHAIN_SERVER_NAME),
                "app_version": str(mlconfig.MLCHAIN_SERVER_VERSION),
            }
        )
        logger.info("Initialized Sentry to {0} and traces_sample_rate: {1} and sample_rate: {2} and drop_modules: {3}".format(mlconfig.MLCHAIN_SENTRY_DSN, mlconfig.MLCHAIN_SENTRY_TRACES_SAMPLE_RATE, mlconfig.MLCHAIN_SENTRY_SAMPLE_RATE, mlconfig.MLCHAIN_SENTRY_DROP_MODULES))
    except sentry_sdk.utils.BadDsn:
        if 'http' in mlconfig.MLCHAIN_SENTRY_DSN:
            raise SystemExit("Sentry DSN configuration is invalid") 

def load_json(path):
    import json
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_yaml(path):
    import yaml
    with open(path) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def load_file(path):
    if isinstance(path, str) and os.path.exists(path):
        if path.endswith('.json'):
            return load_json(path)
        if path.endswith('.yaml') or path.endswith('.yml'):
            return load_yaml(path)
    return None


def get_value(value=None, config=None, key=None, default=None):
    if value is not None:
        return value
    if isinstance(config, dict) and key in config:
        return config[key]
    return default


def load_from_file(path):
    data = load_file(path)
    if data is not None:
        load_config(data)
    else:
        raise AssertionError("Only support config file is json or yaml")
