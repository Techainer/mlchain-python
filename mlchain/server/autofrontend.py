import os
from inspect import signature
from typing import Union
from copy import deepcopy
from mlchain import logger
from werkzeug.datastructures import FileStorage
import numpy as np


class AutofrontendConfig:
    def __init__(self, title='MLChain', description='Autofrontend'):
        # self.id = 0
        # self.summary = {
        #     'id': self.id,
        #     'name': title,
        #     'short_description': description,
        #     'image': '',
        #     'created_at': datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
        #     'status': 'public',
        #     'owner': {
        #         'name': getpass.getuser(),
        #         'id': '0',
        #     }
        # }
        self.input_config = {
            'type': 'multi_scenarios'
        }
        self.input_config['scenarios'] = []

        self.output_config = deepcopy(self.input_config)
        self.config = deepcopy(self.input_config)

    def add_endpoint(self, func, endpoint, name=None, description='',
                     output_config=None, sample_url=None):
        if not description:
            description = getattr(func, '__doc__', None)
        if sample_url is None:
            sample_url = endpoint
        input_config = {
            'params': {
                'from_input': generator_param(func)
            },
            'api_url': endpoint,
            'sample_url': sample_url
        }
        if output_config is None:
            output_config = {
                'preview': [
                    {
                        'type': 'fancy_json',
                        'src': 'output'
                    }
                ]
            }

        scenario = {
            'label': name or getattr(func, '__name__', os.path.basename(endpoint)),
            'input': input_config,
            'output': output_config
        }
        self.input_config['scenarios'].append(
            {
                'label': name or getattr(func, '__name__', os.path.basename(endpoint)),
                'input': input_config,
            }
        )
        self.output_config['scenarios'].append(
            {
                'output': output_config
            }
        )
        self.config['scenarios'].append(scenario)
        return scenario


type_map = {
    str: "text",
    bool: "text",
    int: "text",
    list: "textarea",
    dict: "textarea",
    type(None): "text",
    FileStorage: "file",
    np.ndarray: "file",
    bytes: "file"
}


def generator_param(func):
    inspect_func_ = signature(func)

    return [generate_type(k, v.annotation, v.default)
            for k, v in inspect_func_.parameters.items()]


def generate_type(key, pytype, default=None):
    if pytype in type_map:
        return {
            'type': [type_map[pytype]],
            'label': key.upper(),
            'key': key
        }
    elif pytype == Union:
        return {
            'type': [type_map[v] if v in type_map else "text"
                     for v in pytype.__args__],
            'label': key.upper(),
            'key': key
        }
    else:
        return {
            'type': ["text", "file"],
            'label': key.upper(),
            'key': key
        }


def register_autofrontend(model_id, serve_model, version='latest', endpoint=None):
    mlchain_management = os.getenv('MLCHAIN_URL', None)
    if endpoint is None:
        endpoint = ''
    autofrontend_template = AutofrontendConfig()
    if serve_model.config is not None:
        out_configs = serve_model.config
    else:
        out_configs = {}
    for name, func in serve_model.get_all_func().items():
        if name in out_configs:
            out_config = out_configs[name]
            if 'config' in out_config:
                config = out_config['config']
            else:
                config = None
        else:
            config = None
        autofrontend_template.add_endpoint(func, f'{endpoint}/call/{name}', output_config=config)
    if os.path.exists("Readme.md"):
        description = open("Readme.md", encoding='utf-8').read()
    else:
        description = ""

    if os.path.exists("changelog.md"):
        changelog = open("changelog.md", encoding='utf-8').read()
    else:
        changelog = ""

    if mlchain_management and model_id is not None:
        config_version = {
            "model_id": model_id,
            "version": version,
            "input_config": autofrontend_template.input_config,
            "output_config": autofrontend_template.output_config,
            'endpoint': endpoint,
            'readme': description,
            'changelog': changelog
        }
        try:
            import requests
            res = requests.post(f'{mlchain_management}/version/create', json=config_version)
            logger.info(str(res.json()))
        except Exception as ex:
            logger.error(ex)
