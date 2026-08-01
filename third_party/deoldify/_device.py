import os
import torch
from enum import Enum
from .device_id import DeviceId
import logging

# NOTE:  This must be called first before any torch imports in order to work properly!


class DeviceException(Exception):
    pass


class _Device:
    def __init__(self):
        self._current_device = DeviceId.CPU
        self._backend = "cpu"
        self._init_device()

    def _init_device(self):
        # Check for Intel Extension for PyTorch
        try:
            import intel_extension_for_pytorch as ipex

            if torch.xpu.is_available():
                self._backend = "xpu"
                return
        except ImportError:
            pass

        # Check for CUDA
        if torch.cuda.is_available():
            self._backend = "cuda"
            return

        self._backend = "cpu"

    def is_gpu(self):
        """Returns `True` if the current device is GPU (CUDA or XPU), `False` otherwise."""
        return self.current() is not DeviceId.CPU

    def current(self):
        return self._current_device

    def set(self, device: DeviceId):
        if device == DeviceId.CPU:
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
            self._current_device = DeviceId.CPU
        else:
            # Handle GPU selection
            if self._backend == "cuda":
                os.environ["CUDA_VISIBLE_DEVICES"] = str(device.value)
                torch.backends.cudnn.benchmark = True
            elif self._backend == "xpu":
                # For XPU, we might need different env vars or just rely on index
                # Currently just setting the device ID
                pass

            self._current_device = device

        return device

    def get_torch_device(self):
        if self._current_device == DeviceId.CPU:
            return torch.device("cpu")

        if self._backend == "cuda":
            return torch.device("cuda")
        elif self._backend == "xpu":
            return torch.device("xpu")

        return torch.device("cpu")
