# Parameters of MLchain
__version__ = "0.1.5r5"
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

try:
    import torch

    torch.set_num_thread(1)
except Exception as e:
    pass
