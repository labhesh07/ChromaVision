"""
BasicSR / GFPGAN import torchvision.transforms.functional_tensor, which was removed
in newer torchvision. Patch the module before importing realesrgan or gfpgan.
"""

import sys
import types


def apply_torchvision_shim() -> None:
    if "torchvision.transforms.functional_tensor" in sys.modules:
        return
    import torchvision.transforms.functional as tvF

    mod = types.ModuleType("torchvision.transforms.functional_tensor")
    mod.rgb_to_grayscale = tvF.rgb_to_grayscale
    sys.modules["torchvision.transforms.functional_tensor"] = mod
