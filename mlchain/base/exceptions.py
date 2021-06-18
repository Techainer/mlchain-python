import os 
import traceback
from .log import logger, sentry_ignore_logger
from sentry_sdk import capture_exception
import logging 
from sentry_sdk import add_breadcrumb
import re 

class MlChainError(Exception):
    """Base class for all exceptions."""

    def __init__(self, msg, code='exception', status_code=500):
        super(MlChainError, self).__init__(msg)
        self.msg = msg
        self.message = msg
        self.code = code
        self.status_code = status_code
        sentry_ignore_logger.error("[{0}]: {1}".format(code, msg))
        sentry_ignore_logger.debug(traceback.format_exc())

class MLChainAssertionError(MlChainError):
    def __init__(self, msg, code="assertion", status_code=422):
        MlChainError.__init__(self, msg, code, status_code)


class MLChain404Error(MlChainError):
    def __init__(self, msg, code="404", status_code=404):
        MlChainError.__init__(self, msg, code, status_code)


class MLChainSerializationError(MlChainError):
    def __init__(self, msg, code="serialization", status_code=422):
        MlChainError.__init__(self, msg, code, status_code)


class MLChainUnauthorized(MlChainError):
    def __init__(self, msg, code="unauthorized", status_code=401):
        MlChainError.__init__(self, msg, code, status_code)

class MLChainConnectionError(MlChainError):
    def __init__(self, msg, code="connection_error", status_code=500):
        MlChainError.__init__(self, msg, code, status_code)

class MLChainTimeoutError(MlChainError):
    def __init__(self, msg, code="timeout", status_code=500):
        MlChainError.__init__(self, msg, code, status_code)

class MLChainConfigError(MlChainError):
    def __init__(self, msg, code="config", status_code=500):
        MlChainError.__init__(self, msg, code, status_code)