# Parameters of MLchain
__version__ = "0.1.8rc1"
HOST = "https://www.api.mlchain.ml"
WEB_HOST = HOST
API_ADDRESS = HOST
MODEL_ID = None
from os import environ

environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
from mlchain.base.log import logger
from .context import mlchain_context

from .base.exceptions import *
from .config import mlconfig