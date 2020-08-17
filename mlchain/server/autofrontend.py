from inspect import signature
from typing import *
from copy import deepcopy
import datetime
from werkzeug.datastructures import FileStorage
import numpy as np
import os
import getpass


class AutofrontendConfig:
    def __init__(self, server_url='localhost:5000', title='MLChain', description='Autofrontend' ):
        self.id = 0
        self.summary = {
            'id': self.id,
            'name': title,
            'short_description': description,
            'image': '',
            'created_at': datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"),
            'status': 'public',
            'owner': {
                'name': getpass.getuser(),
                'id': '0',
            }
        }
        self.input_config = {
            'type':'multi_scenarios'
        }
        self.input_config['scenarios'] = []

        self.output_config = deepcopy(self.input_config)
        self.config = deepcopy(self.input_config)

    def add_endpoint(self, func, endpoint, name=None, description='', output_config=None,sample_url = None):
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
                'output':output_config
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

    return [generate_type(k, v.annotation, v.default) for k, v in inspect_func_.parameters.items()]


def generate_type(key, pytype, default=None):
    if pytype in type_map:
        return {
            'type': [type_map[pytype]],
            'label': key.upper(),
            'key': key
        }
    elif pytype == Union:
        return {
            'type': [type_map[v] if v in type_map else "text" for v in pytype.__args__],
            'label': key.upper(),
            'key': key
        }
    else:
        return {
            'type': ["text", "file"],
            'label': key.upper(),
            'key': key
        }
