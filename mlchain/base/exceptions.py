from .log import logger
import traceback


class MlChainError(Exception):
    """Base class for all exceptions."""

    def __init__(self, msg, code='exception', status_code=500):
        self.msg = msg
        self.code = code
        self.status_code = status_code
        logger.error("[{0}]: {1}".format(code, msg))
        logger.debug(traceback.format_exc())


class MLChainAssertionError(MlChainError):
    def __init__(self, msg, code="assertion", status_code=422):
        MlChainError.__init__(self, msg, code, status_code)


class MLChainSerializationError(MlChainError):
    def __init__(self, msg, code="serialization", status_code=422):
        MlChainError.__init__(self, msg, code, status_code)


class MLChainUnauthorized(MlChainError):
    def __init__(self, msg, code="unauthorized", status_code=401):
        MlChainError.__init__(self, msg, code, status_code)
