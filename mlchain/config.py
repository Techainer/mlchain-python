from os import environ
import os
from collections import defaultdict

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
        r = self.get_default(item)
        return r

    def get_item(self, item):
        if item.upper() in self:
            return self[item.upper()]

        r = environ.get(self.env_key.upper() + item)
        if r is not None:
            return r

        r = environ.get(self.env_key.lower() + item)
        if r is not None:
            return r

        r = environ.get(item)
        return r

    def from_json(self, path):
        import json
        self.update(json.load(open(path, encoding='utf-8')))

    def from_yaml(self, path):
        import yaml
        self.update(yaml.load(open(path)))

    def update(self, data):
        for k, v in data.items():
            self[k.upper()] = v

    def get_default(self, item):
        key = item.upper()
        if not key.endswith('_DEFAULT'):
            key += '_DEFAULT'
        if key in self:
            return self[key]
        else:
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
    def update_client(self,clients):
        self.clients.update({k.upper():v for k,v in clients.items()})
    def load_config(self, path, mode = None):
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
                            environ[k] = str(v)
                        self.update(data['mode']['env'][mode])

    def get_client_config(self,name):
        name = name.upper()
        return BaseConfig(env_key='CLIENT_{0}_'.format(name),**self.clients[name])

mlconfig = MLConfig(env_key='')

all_configs = [object_storage_config]


def artifact(action, data, force=False, names=None):
    if 'artifact' in data:
        artifact = data['artifact']
        from mlchain.storage.object_storage import ObjectStorage
        for source in artifact:
            storage = ObjectStorage(bucket=source.get('bucket', None), url=source.get('url', None),
                                    access_key=source.get('access_key'), secret_key=source.get('secret_key', None),
                                    provider=source.get('provider', None))
            for download in source.get('mapping', []):
                d_remote = download.get('remote', None)
                d_local = download.get('local', None)
                d_type = download.get('type', None)
                bucket = download.get('bucket', None)
                d_name = download.get('name', None)
                if d_remote is not None and d_local is not None and d_type is not None \
                        and (d_name is None or names is None or len(names) == 0 or d_name in names):
                    if action == 'pull':
                        if force or not os.path.exists(d_local):
                            if d_type == 'file':
                                storage.download_file(d_remote, d_local, bucket)
                            elif d_type == 'folder':
                                storage.download_dir(d_remote, d_local, bucket)
                            else:
                                raise Exception('artifact type is file or folder')
                    elif action == 'push':
                        if d_type == 'file':
                            storage.upload_file(d_local, d_remote, bucket, overwrite=force)
                        elif d_type == 'folder':
                            storage.upload_dir(d_local, d_remote, bucket)
                        else:
                            raise Exception('artifact type is file or folder')
    else:
        raise Exception("Not found artifact in config")


def load_config(data):
    for config in all_configs:
        env_key = config.env_key.strip('_').lower()
        if env_key in data:
            config.update(data[env_key])
    if 'clients' in data:
        mlconfig.update_client(data['clients'])
    if 'mode' in data:
        if 'default' in data['mode']:
            default = data['mode']['default']
        else:
            default = 'default'

        if 'env' in data['mode']:
            for mode in ['default', default]:
                if mode in data['mode']['env']:
                    for k, v in data['mode']['env'][mode].items():
                        environ[k] = str(v)
                    mlconfig.update(data['mode']['env'][mode])


def load_json(path):
    import json
    return json.load(open(path, encoding='utf-8'))


def load_yaml(path):
    import yaml
    return yaml.load(open(path))


def get_value(value=None, config=None, key=None, default=None):
    if value is not None:
        return value
    if isinstance(config, dict) and key in config:
        return config[key]
    return default


def load_from_file(path):
    if isinstance(path, str) and os.path.exists(path):
        if path.endswith('.json'):
            load_config(load_json(path))
        elif path.endswith('.yaml') or path.endswith('.yml'):
            load_config(load_yaml(path))
        else:
            raise AssertionError("Only support config file is json or yaml")
