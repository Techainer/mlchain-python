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

class GPUStats:
    def __init__(self):
        try:
            nvmlInit()
            self.has_gpu = True
        except Exception as error:
            logger.debug(f"Cannot get GPU info: {error}")
            self.has_gpu = False
        if self.has_gpu:
            self.gpu_count = nvmlDeviceGetCount()

    def get_gpu_statistics(self):
        """Get statistics for each GPU installed in the system."""
        if not self.has_gpu:
            return []
        statistics = []
        for i in range(self.gpu_count):
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
        return statistics

gpu_stats = GPUStats()

def get_gpu_statistics():
    return gpu_stats.get_gpu_statistics()