"""
The code is referenced from https://github.com/jacenkow/gpu-sentry/blob/master/gpu_sentry/client.py
"""
from pynvml import (
    NVMLError,
    nvmlDeviceGetCount,
    nvmlDeviceGetHandleByIndex,
    nvmlDeviceGetMemoryInfo,
    nvmlDeviceGetName,
    nvmlInit,
)
from mlchain.base.log import logger

def _convert_kb_to_gb(size):
    """Convert given size in kB to GB with 2-decimal places rounding."""
    return round(size / 1024 ** 3, 2)

def get_gpu_statistics():
    """Get statistics for each GPU installed in the system."""
    statistics = []
    try:
        nvmlInit()

        count = nvmlDeviceGetCount()
        for i in range(count):
            handle = nvmlDeviceGetHandleByIndex(i)

            memory = nvmlDeviceGetMemoryInfo(handle)

            statistics.append({
                "gpu": i,
                "name": nvmlDeviceGetName(handle).decode("utf-8"),
                "memory": {
                    "total": _convert_kb_to_gb(int(memory.total)),
                    "used": _convert_kb_to_gb(int(memory.used)),
                    "utilisation": int(memory.used / memory.total * 100)
                },
            })
    except Exception as error:
        logger.debug("Get GPU info from NVMLError error {0}".format(error))

    return statistics