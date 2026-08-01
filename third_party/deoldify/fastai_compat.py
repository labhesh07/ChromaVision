"""
FastAI compatibility layer for DeOldify.
Provides minimal shims to run inference without the full FastAI library.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor
from torch.nn.utils import weight_norm, spectral_norm
from typing import List, Tuple, Callable, Optional, Union, Any
from enum import Enum
from pathlib import Path
import numpy as np

# Type aliases
Sizes = List[Tuple[int, ...]]  # List of tensor shapes


def ifnone(a, b):
    """Return b if a is None, else a."""
    return b if a is None else a


def noop(x=None, *args, **kwargs):
    """Does nothing (used as placeholder)."""
    return x


def init_default(m, func=nn.init.kaiming_normal_):
    """Initialize weights of a module using the given function."""
    if hasattr(m, "weight") and hasattr(m.weight, "data"):
        func(m.weight.data)
    if hasattr(m, "bias") and hasattr(m.bias, "data"):
        m.bias.data.zero_()
    return m


class DataBunch:
    """Minimal DataBunch shim."""

    def __init__(self, c=3, device=None, **kwargs):
        self.c = c
        if device:
            self.device = device
        else:
            from deoldify import device as device_settings

            self.device = device_settings.get_torch_device()


def _identity_param(p):
    """Identity function for parameters."""
    return p


import torchvision.models as models


class NormType(Enum):
    Batch = 1
    BatchZero = 2
    Weight = 3
    Spectral = 4
    Instance = 5
    InstanceZero = 6
    Pixel = 7


SplitFuncOrIdxList = Optional[Union[Callable, List[int]]]


def to_device(m, device):
    return m.to(device)


def apply_init(m, init_func):
    if hasattr(m, "apply"):
        m.apply(
            lambda x: (
                init_func(x.weight)
                if hasattr(x, "weight") and hasattr(x.weight, "data")
                else None
            )
        )


ImageDataBunch = DataBunch


def camel2snake(name):
    import re

    _camel_re1 = re.compile("(.)([A-Z][a-z]+)")
    _camel_re2 = re.compile("([a-z0-9])([A-Z])")
    return _camel_re2.sub(r"\1_\2", _camel_re1.sub(r"\1_\2", name)).lower()


class SequentialEx(nn.Module):
    "Like `nn.Sequential`, but with ModuleList semantics, and can handle `MergeLayer`."

    def __init__(self, *layers):
        super().__init__()
        self.layers = nn.ModuleList(layers)

    def forward(self, x):
        res = x
        for l in self.layers:
            res.orig = x
            nres = l(res)
            # We have to remove res.orig to avoid hanging references and therefore memory leaks
            res.orig = None
            res = nres
        return res

    def __getitem__(self, i):
        return self.layers[i]

    def append(self, l):
        return self.layers.append(l)

    def extend(self, l):
        return self.layers.extend(l)

    def insert(self, i, l):
        return self.layers.insert(i, l)


class MergeLayer(nn.Module):
    "Merge a shortcut with the result of the module by adding them or concatenating them if `dense=True`."

    def __init__(self, dense: bool = False):
        super().__init__()
        self.dense = dense

    def forward(self, x):
        return torch.cat([x, x.orig], dim=1) if self.dense else (x + x.orig)


class SigmoidRange(nn.Module):
    "Sigmoid module with range `(low, x_max)`"

    def __init__(self, low, high):
        super().__init__()
        self.low, self.high = low, high

    def forward(self, x):
        return torch.sigmoid(x) * (self.high - self.low) + self.low


def conv_layer(
    ni: int,
    nf: int,
    ks: int = 3,
    stride: int = 1,
    padding: int = None,
    bias: bool = None,
    is_1d: bool = False,
    norm_type: Optional[str] = None,
    use_activ: bool = True,
    leaky: float = None,
    transpose: bool = False,
    init: Callable = nn.init.kaiming_normal_,
    self_attention: bool = False,
):
    "Create a sequence of convolutional (`ni` to `nf`), ReLU (if `use_activ`) and batchnorm (if `bn`) layers."
    if padding is None:
        padding = (ks - 1) // 2 if not transpose else 0
    bn = norm_type in (NormType.Batch, NormType.BatchZero)
    if bias is None:
        bias = not bn
    conv_func = nn.ConvTranspose2d if transpose else nn.Conv1d if is_1d else nn.Conv2d
    conv = conv_func(ni, nf, kernel_size=ks, bias=bias, stride=stride, padding=padding)

    if init:
        init(conv.weight)

    if norm_type == NormType.Weight:
        conv = weight_norm(conv)
    elif norm_type == NormType.Spectral:
        conv = spectral_norm(conv)

    layers = [conv]
    if use_activ:
        layers.append(relu(leaky=leaky))
    if bn:
        layers.append((nn.BatchNorm1d if is_1d else nn.BatchNorm2d)(nf))
    if self_attention:
        layers.append(SelfAttention(nf))
    return nn.Sequential(*layers)


def relu(inplace: bool = True, leaky: float = None):
    return (
        nn.LeakyReLU(ifnone(leaky, 0.1), inplace=inplace)
        if leaky is not None
        else nn.ReLU(inplace=inplace)
    )


def batchnorm_2d(nf: int, norm_type: str = "Batch"):
    return nn.BatchNorm2d(nf)


def icnr(x, scale=2, init=nn.init.kaiming_normal_):
    """ICNR init for PixelShuffle to avoid checkerboard artifacts.

    See: https://arxiv.org/abs/1707.02937
    """
    ni, nf, h, w = x.shape
    ni2 = int(ni / (scale**2))
    k = init(torch.zeros([ni2, nf, h, w])).transpose(0, 1)
    k = k.contiguous().view(ni2, nf, -1)
    k = k.repeat(1, 1, scale**2)
    k = k.contiguous().view([nf, ni, h, w]).transpose(0, 1)
    x.data.copy_(k)


class PixelShuffle_ICNR(nn.Module):
    """PixelShuffle upsampling with ICNR initialization."""

    def __init__(
        self,
        ni: int,
        nf: int = None,
        scale: int = 2,
        blur: bool = False,
        norm_type: Optional[NormType] = NormType.Weight,
        leaky: float = None,
    ):
        super().__init__()
        nf = ifnone(nf, ni)
        self.conv = conv_layer(
            ni, nf * (scale**2), ks=1, norm_type=norm_type, use_activ=False
        )
        icnr(self.conv[0].weight)
        self.shuf = nn.PixelShuffle(scale)
        self.pad = nn.ReplicationPad2d((1, 0, 1, 0))
        self.blur = nn.AvgPool2d(2, stride=1)
        self.do_blur = blur
        self.relu = relu(True, leaky=leaky)

    def forward(self, x):
        x = self.shuf(self.relu(self.conv(x)))
        return self.blur(self.pad(x)) if self.do_blur else x


class SelfAttention(nn.Module):
    "Self attention layer for nd."

    def __init__(self, n_channels: int):
        super().__init__()
        self.query = conv1d(n_channels, n_channels // 8)
        self.key = conv1d(n_channels, n_channels // 8)
        self.value = conv1d(n_channels, n_channels)
        self.gamma = nn.Parameter(tensor([0.0]))

    def forward(self, x):
        # Notation from https://arxiv.org/abs/1805.08318
        size = x.size()
        x = x.view(*size[:2], -1)
        f, g, h = self.query(x), self.key(x), self.value(x)
        beta = F.softmax(torch.bmm(f.transpose(1, 2), g), dim=1)
        o = self.gamma * torch.bmm(h, beta) + x
        return o.view(*size)


def conv1d(
    ni: int, no: int, ks: int = 1, stride: int = 1, padding: int = 0, bias: bool = False
):
    "Create and initialize a `nn.Conv1d` layer with spectral normalization."
    conv = nn.Conv1d(ni, no, ks, stride=stride, padding=padding, bias=bias)
    nn.init.kaiming_normal_(conv.weight)
    if bias:
        conv.bias.data.zero_()
    return spectral_norm(conv)


def res_block(
    nf, dense: bool = False, norm_type: str = "Batch", bottle: bool = False, **kwargs
):
    "Resnet block of `nf` features."
    norm2 = norm_type
    if not dense and (norm_type == "Batch"):
        norm2 = "BatchZero"
    nf_inner = nf // 2 if bottle else nf
    return SequentialEx(
        conv_layer(nf, nf_inner, norm_type=norm_type, **kwargs),
        conv_layer(nf_inner, nf, norm_type=norm2, **kwargs),
        MergeLayer(dense),
    )


# --- Hooks & Model Sizes ---


class Hook:
    "Create a hook on `m` with `hook_func`."

    def __init__(
        self,
        m: nn.Module,
        hook_func: Callable,
        is_forward: bool = True,
        detach: bool = True,
    ):
        self.hook_func, self.detach, self.stored = hook_func, detach, None
        f = m.register_forward_hook if is_forward else m.register_backward_hook
        self.hook = f(self.hook_fn)
        self.removed = False

    def hook_fn(self, module: nn.Module, input: Tensor, output: Tensor):
        if self.detach:
            input = (
                (o.detach() for o in input)
                if isinstance(input, tuple)
                else input.detach()
            )
            output = (
                (o.detach() for o in output)
                if isinstance(output, tuple)
                else output.detach()
            )
        self.stored = self.hook_func(module, input, output)

    def remove(self):
        if not self.removed:
            self.hook.remove()
            self.removed = True

    def __enter__(self, *args):
        return self

    def __exit__(self, *args):
        self.remove()


class Hooks:
    "Create several hooks on the modules in `ms` with `hook_func`."

    def __init__(
        self,
        ms: List[nn.Module],
        hook_func: Callable,
        is_forward: bool = True,
        detach: bool = True,
    ):
        self.hooks = [Hook(m, hook_func, is_forward, detach) for m in ms]

    def __getitem__(self, i: int) -> Hook:
        return self.hooks[i]

    def __len__(self) -> int:
        return len(self.hooks)

    def __iter__(self):
        return iter(self.hooks)

    @property
    def stored(self):
        return [o.stored for o in self]

    def remove(self):
        for h in self.hooks:
            h.remove()

    def __enter__(self, *args):
        return self

    def __exit__(self, *args):
        self.remove()


def _hook_inner(m, i, o):
    return o if isinstance(o, Tensor) else o if isinstance(o, list) else list(o)


def hook_outputs(
    modules: List[nn.Module], detach: bool = True, grad: bool = False
) -> Hooks:
    "Return `Hooks` that store activations of all `modules` in `self.stored`"
    return Hooks(modules, _hook_inner, detach=detach, is_forward=not grad)


def dummy_eval(m: nn.Module, size: Tuple = (64, 64)):
    "Evaluate `m` on a dummy input of a certain `size`"
    ch_in = in_channels(m)
    x = torch.randn(1, ch_in, *size)
    if next(m.parameters()).is_cuda:
        x = x.cuda()
    return m.eval()(x)


def model_sizes(m: nn.Module, size: Tuple = (64, 64)):
    "Pass a dummy input through the model `m` to get the various sizes of activations."
    with hook_outputs(m) as hooks:
        dummy_eval(m, size)
        return [o.stored.shape for o in hooks]


def in_channels(m: nn.Module) -> int:
    "Return the shape of the first weight layer in `m`."
    for l in m.modules():
        if isinstance(l, (nn.Conv1d, nn.Conv2d, nn.Conv3d)):
            return l.in_channels
    raise Exception("No weight layer")


# --- Model Creation ---


def create_body(
    arch: Callable, pretrained: bool = True, cut: Optional[Union[int, Callable]] = None
):
    "Cut off the head of a typically pretrained `arch`."
    model = arch(pretrained=pretrained)
    # Most torchvision models have 'fc' or 'classifier' as head
    # ResNet specific cut
    if cut is None:
        ll = list(enumerate(model.children()))
        cut = next(i for i, o in reversed(ll) if has_pool_type(o))

    return nn.Sequential(*list(model.children())[:cut])


def has_pool_type(m):
    if isinstance(
        m, (nn.AdaptiveAvgPool2d, nn.AdaptiveMaxPool2d, nn.AvgPool2d, nn.MaxPool2d)
    ):
        return True
    return False


def cnn_config(arch):
    "Get the metadata for `arch`."
    # Simplified config for ResNets
    return {"split": lambda m: (m[0][6], m[1])}  # Split at layer 6 for ResNet


# --- Learner Shim ---


class Learner:
    "Minimal Learner shim for inference."

    def __init__(self, data, model, path=None, **kwargs):
        self.data = data
        self.model = model
        self.path = path

        # Use deoldify.device to get the correct device (CUDA/XPU/CPU)
        from deoldify import device as device_settings

        self.device = device_settings.get_torch_device()

        self.model.to(self.device)

    def load(self, name):
        # Load state dict
        if self.path:
            path = self.path / "models" / f"{name}.pth"
        else:
            path = f"models/{name}.pth"

        # Handle map_location
        state = torch.load(path, map_location=self.device, weights_only=False)
        if "model" in state:
            state = state["model"]
        self.model.load_state_dict(state, strict=True)

    def split(self, split_on):
        pass  # Not needed for inference

    def freeze(self):
        for p in self.model.parameters():
            p.requires_grad = False


class DataBunch:
    "Minimal DataBunch shim."

    def __init__(self, c=3, device=None, **kwargs):
        self.c = c
        if device:
            self.device = device
        else:
            from deoldify import device as device_settings

            self.device = device_settings.get_torch_device()


def get_dummy_databunch():
    return DataBunch()


def tensor(x, *args, **kwargs):
    return torch.tensor(x, *args, **kwargs)
