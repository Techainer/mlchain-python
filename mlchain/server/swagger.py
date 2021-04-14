from inspect import signature, _empty
from typing import List, Dict, Union
from copy import deepcopy
import json
from werkzeug.datastructures import FileStorage
import numpy as np
from mlchain import __version__, HOST


class SwaggerTemplate:
    def __init__(self, server_url='/', tags=None, title='MLChain',
                 description='Swagger', version=__version__):
        self.template = {
            "openapi": "3.0.0",
            "info": {
                "title": title,
                "description": description,
                "version": version
            },
            "servers": [
                {
                    "url": server_url,
                    "description": HOST
                }
            ],
            "tags": tags,
            "paths": {}
        }

    def add_core_endpoint(self, func, endpoint, tags=None, summary='',
                     description='', description_output=''):
        if not description:
            description = getattr(func, '__doc__', None)
        post_format = {
            "tags": tags,
            "summary": summary if len(summary) > 0 else description[:80].split(":")[0] if description is not None else summary,
            "description": description,
            "responses": {
                "200": {
                    "description": "OK"
                }
            }
        }

        if '{function_name}' in endpoint: 
            post_format['parameters'] = [
                {
                    "name": "function_name",
                    "in": "path",
                    "description": "Function Name",
                    "required": True,
                    "schema": {
                        "type": "string"
                    }
                }
            ]

        self.template['paths'][endpoint] = {
            'get': post_format}

    def add_endpoint(self, func, endpoint, tags=None, summary='',
                     description='', description_output=''):
        if not description:
            description = getattr(func, '__doc__', None)
        post_format = {
            "tags": tags,
            "summary": summary if len(summary) > 0 else description[:80].split(":")[0] if description is not None else summary,
            "description": description,
            "requestBody": {
                "required": True,
                "content": {
                    "multipart/form-data": {
                        "schema": {
                            'type': 'object',
                            'properties': generator_param(func)
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": description_output if len(description_output) > 0 else "The server already get the valid request",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "output": {
                                        "type": "object",
                                        "description": "The true output of API"
                                    },
                                    "time": {
                                        "type": "number",
                                        "format": "decimal",
                                        "description": "The processed time"
                                    },
                                    "api_version": {
                                        "type": "string",
                                        "description": "The version of API"
                                    },
                                    "mlchain_version": {
                                        "type": "string",
                                        "description": "The version of Mlchain"
                                    },
                                    "request_id": {
                                        "type": "string",
                                        "description": "The ID of request to trace"
                                    },
                                }
                            }
                        }
                    }
                },
                "500": {
                    "description": "The server has error with this request",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {
                                        "type": "object",
                                        "description": "The detail error"
                                    },
                                    "time": {
                                        "type": "number",
                                        "format": "decimal",
                                        "description": "The processed time"
                                    },
                                    "api_version": {
                                        "type": "string",
                                        "description": "The version of API"
                                    },
                                    "mlchain_version": {
                                        "type": "string",
                                        "description": "The version of Mlchain"
                                    },
                                    "request_id": {
                                        "type": "string",
                                        "description": "The ID of request to trace"
                                    },
                                }
                            }
                        }
                    }
                }, 
                "422": {
                    "description": "The input is not valid, please check!",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {
                                        "type": "string",
                                        "description": "The detail error"
                                    },
                                    "time": {
                                        "type": "number",
                                        "format": "decimal",
                                        "description": "The processed time"
                                    },
                                    "api_version": {
                                        "type": "string",
                                        "description": "The version of API"
                                    },
                                    "mlchain_version": {
                                        "type": "string",
                                        "description": "The version of Mlchain"
                                    },
                                    "request_id": {
                                        "type": "string",
                                        "description": "The ID of request to trace"
                                    },
                                }
                            }
                        }
                    }
                }
            }
        }

        self.template['paths'][endpoint] = {
            'post': post_format}

    def save(self, path):
        import pprint
        pprint.pprint(self.template)
        json.dump(self.template, open(path, 'w', encoding='utf-8'))


type_map = {
    str: {
        "type": "string"
    },
    bool: {
        "type": "boolean"
    },
    float: {
        'type': 'number',
        'format': 'float',
    },
    int: {
        "type": "integer",
        "format": "int32"
    },
    list: {
        "type": "array",
        "items": {}
    },
    type(None): {
        "type": {}
    },
    FileStorage: {
        "type": "string",
        "format": "binary"
    },
    np.ndarray: {
        "type": "string",
        "format": "binary"
    },
    List[np.ndarray]: {
        "type": "string",
        "format": "binary"
    },
    bytes: {
        "type": "string",
        "format": "binary"
    }
}


def generator_param(func):
    inspect_func_ = signature(func)
    return {k: generate_type(v.annotation, v.default)
            for k, v in inspect_func_.parameters.items()}


def generate_type(pytype, default=None):
    if pytype in type_map:
        swagger_type = deepcopy(type_map[pytype])
        if default is not None and default != _empty:
            swagger_type['default'] = default
        return swagger_type
    if pytype in (Dict, dict):
        return {
            'type': 'object',
            'properties': get_example_dict(default)
        }
    if pytype == Union:
        return {
            'type': [generate_type(v) for v in pytype.__args__]
        }
    return deepcopy(type_map[type(None)])


def get_example_dict(exmaple):
    if isinstance(exmaple, (Dict, dict)):
        return {k: generate_type(type(v), v) for k, v in exmaple.items()}
    else:
        return {}
