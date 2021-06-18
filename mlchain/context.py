"""
Mlchain Context
Borrowed a little from: https://github.com/tomwojcik/starlette-context. Thanks for the contribution!
"""
import contextvars
import copy

from collections import UserDict
from contextvars import copy_context
from typing import Any
from mlchain import _request_scope_context_storage

class MLChainContext(UserDict):
    """
    A mapping with dict-like interface.
    """
    def __init__(self, *args: Any, **kwargs: Any):
        # not calling super on purpose
        if args or kwargs:
            raise AttributeError("Can't instantiate with attributes")

    @property
    def data(self) -> dict:  # type: ignore
        """
        Dump this to json. Object itself it not serializable.
        """
        try:
            return _request_scope_context_storage.get()
        except LookupError as e:
            variables = {}
            _request_scope_context_storage.set(variables)

            return _request_scope_context_storage.get()

    @property
    def exists(self) -> bool:
        return _request_scope_context_storage in copy_context()

    def to_dict(self) -> dict:
        return self.data

    def copy(self) -> dict:
        return copy.copy(self.data)

    def set(self, variables: dict):
        _request_scope_context_storage.set(variables)

        return variables

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except: 
            return None 

    def set_mlchain_context_id(self, value: str):
        if not self.exists: 
            self.set({"MLCHAIN_CONTEXT_ID": value})
            return value

        self.update({"MLCHAIN_CONTEXT_ID": value})
        return value

mlchain_context = MLChainContext()