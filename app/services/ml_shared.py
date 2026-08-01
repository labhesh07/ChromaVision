"""Lazy-loaded Real-ESRGAN (shared) and GFPGAN restorer."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import cv2
import numpy as np
import torch
from PIL import Image

from app.config import Settings, get_settings
from app.torchvision_shim import apply_torchvision_shim

if TYPE_CHECKING:
    pass

_lock = threading.RLock()
_realesrgan_upsampler = None
_gfpgan_restorer = None
_advanced_realesrgan_upsampler = None
_advanced_gfpgan_restorer = None


def resolve_device(settings: Settings) -> torch.device:
    if settings.device.lower() == "cpu":
        return torch.device("cpu")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def _maybe_downscale_bgr(img: np.ndarray, max_edge: int) -> np.ndarray:
    if max_edge <= 0:
        return img
    h, w = img.shape[:2]
    m = max(h, w)
    if m <= max_edge:
        return img
    scale = max_edge / float(m)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    return cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)


def pil_rgb_to_bgr_cv2(im: Image.Image) -> np.ndarray:
    arr = np.asarray(im.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def bgr_cv2_to_pil_rgb(arr: np.ndarray) -> Image.Image:
    rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb, mode="RGB")


def _pre_restore_denoise(bgr: np.ndarray, settings: Settings) -> np.ndarray:
    """Optional pre-scrub to suppress grain/speckle before restoration."""
    if not settings.restore_denoise:
        return bgr
    h = max(1, int(settings.denoise_strength))
    hc = max(1, int(settings.denoise_color_strength))
    return cv2.fastNlMeansDenoisingColored(bgr, None, h, hc, 7, 21)


def _pre_restore_denoise_advanced(bgr: np.ndarray, settings: Settings) -> np.ndarray:
    if not settings.advanced_denoise:
        return bgr
    h = max(1, int(settings.advanced_denoise_strength))
    hc = max(1, int(settings.advanced_denoise_color_strength))
    return cv2.fastNlMeansDenoisingColored(bgr, None, h, hc, 7, 21)


def get_realesrgan(settings: Settings | None = None):
    """
    Singleton RealESRGANer.
    Supports:
      - general_x4v3 (SRVGG, faster)
      - x4plus (RRDBNet, higher quality)
    """
    global _realesrgan_upsampler
    settings = settings or get_settings()
    with _lock:
        if _realesrgan_upsampler is not None:
            return _realesrgan_upsampler
        apply_torchvision_shim()
        from realesrgan import RealESRGANer

        device = resolve_device(settings)
        model_name = settings.realesrgan_model.strip().lower()
        if model_name == "x4plus":
            from basicsr.archs.rrdbnet_arch import RRDBNet

            wpath = settings.realesrgan_x4plus_weights
            if not wpath.is_file():
                # Graceful fallback to lightweight model if x4plus weights are absent.
                model_name = "general_x4v3"
        if model_name == "general_x4v3":
            from realesrgan.archs.srvgg_arch import SRVGGNetCompact

            wpath = settings.realesrgan_weights
            if not wpath.is_file():
                raise FileNotFoundError(
                    f"Real-ESRGAN weights not found at {wpath}. "
                    "Run scripts/download_weights.py or place realesr-general-x4v3.pth there."
                )
            model = SRVGGNetCompact(
                num_in_ch=3,
                num_out_ch=3,
                num_feat=64,
                num_conv=32,
                upscale=4,
                act_type="prelu",
            )
        elif model_name == "x4plus":
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        else:
            raise ValueError(f"Unsupported realesrgan_model: {settings.realesrgan_model}")
        half = device.type == "cuda"
        _realesrgan_upsampler = RealESRGANer(
            scale=4,
            model_path=str(wpath),
            model=model,
            tile=max(0, int(settings.realesrgan_tile)),
            tile_pad=max(0, int(settings.realesrgan_tile_pad)),
            pre_pad=max(0, int(settings.realesrgan_pre_pad)),
            half=half,
            device=device,
        )
        return _realesrgan_upsampler


def get_gfpgan(settings: Settings | None = None):
    """GFPGAN with Real-ESRGAN as background upsampler (shared instance)."""
    global _gfpgan_restorer
    settings = settings or get_settings()
    with _lock:
        if _gfpgan_restorer is not None:
            return _gfpgan_restorer
        apply_torchvision_shim()
        from gfpgan import GFPGANer

        wpath = settings.gfpgan_weights
        if not wpath.is_file():
            raise FileNotFoundError(
                f"GFPGAN weights not found at {wpath}. "
                "Run scripts/download_weights.py or place GFPGANv1.4.pth there."
            )

        device = resolve_device(settings)
        bg = get_realesrgan(settings)
        _gfpgan_restorer = GFPGANer(
            model_path=str(wpath),
            upscale=max(1, int(settings.restore_upscale)),
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=bg,
            device=device,
        )
        return _gfpgan_restorer


def get_realesrgan_advanced(settings: Settings | None = None):
    """Dedicated pro pipeline: x4plus RRDBNet with tiling."""
    global _advanced_realesrgan_upsampler
    settings = settings or get_settings()
    with _lock:
        if _advanced_realesrgan_upsampler is not None:
            return _advanced_realesrgan_upsampler
        apply_torchvision_shim()
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer

        wpath = settings.realesrgan_x4plus_weights
        if not wpath.is_file():
            raise FileNotFoundError(
                f"Advanced upscaler requires RealESRGAN_x4plus at {wpath}. "
                "Run scripts/download_weights.py."
            )

        device = resolve_device(settings)
        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
        half = device.type == "cuda"
        try:
            _advanced_realesrgan_upsampler = RealESRGANer(
                scale=4,
                model_path=str(wpath),
                model=model,
                tile=max(0, int(settings.advanced_tile)),
                tile_pad=max(0, int(settings.advanced_tile_pad)),
                pre_pad=max(0, int(settings.advanced_pre_pad)),
                half=half,
                device=device,
            )
        except Exception as e:
            raise FileNotFoundError(
                f"Advanced x4plus weights could not be loaded from {wpath}. "
                "Re-download using scripts/download_weights.py."
            ) from e
        return _advanced_realesrgan_upsampler


def get_gfpgan_advanced(settings: Settings | None = None):
    """GFPGAN with advanced RRDB x4plus background upsampler at aligned upscale factor."""
    global _advanced_gfpgan_restorer
    settings = settings or get_settings()
    with _lock:
        if _advanced_gfpgan_restorer is not None:
            return _advanced_gfpgan_restorer
        apply_torchvision_shim()
        from gfpgan import GFPGANer

        wpath = settings.gfpgan_weights
        if not wpath.is_file():
            raise FileNotFoundError(
                f"GFPGAN weights not found at {wpath}. "
                "Run scripts/download_weights.py or place GFPGANv1.4.pth there."
            )

        device = resolve_device(settings)
        bg = get_realesrgan_advanced(settings)
        try:
            _advanced_gfpgan_restorer = GFPGANer(
                model_path=str(wpath),
                upscale=max(1, int(settings.advanced_upscale_factor)),
                arch="clean",
                channel_multiplier=2,
                bg_upsampler=bg,
                device=device,
            )
        except Exception as e:
            raise FileNotFoundError(
                f"GFPGAN weights could not be loaded from {wpath}. "
                "Re-download using scripts/download_weights.py."
            ) from e
        return _advanced_gfpgan_restorer


def run_upscale(pil_im: Image.Image, settings: Settings | None = None) -> Image.Image:
    settings = settings or get_settings()
    upsampler = get_realesrgan(settings)
    bgr = pil_rgb_to_bgr_cv2(pil_im)
    # When tiling is enabled, avoid shrinking input first.
    if settings.realesrgan_tile <= 0:
        bgr = _maybe_downscale_bgr(bgr, settings.max_input_edge)
    out_bgr, _ = upsampler.enhance(bgr, outscale=4)
    return bgr_cv2_to_pil_rgb(out_bgr)


def run_restore(pil_im: Image.Image, settings: Settings | None = None) -> Image.Image:
    """Face restoration + BG upscale; works on non-face images (background-only path)."""
    settings = settings or get_settings()
    restorer = get_gfpgan(settings)
    bgr = pil_rgb_to_bgr_cv2(pil_im)
    bgr = _pre_restore_denoise(bgr, settings)
    if settings.realesrgan_tile <= 0:
        bgr = _maybe_downscale_bgr(bgr, settings.max_input_edge)
    _, _, restored = restorer.enhance(bgr, has_aligned=False, only_center_face=False, paste_back=True)
    if restored is None:
        return pil_im
    return bgr_cv2_to_pil_rgb(restored)


def run_advanced_upscale(pil_im: Image.Image, settings: Settings | None = None) -> Image.Image:
    """
    Separate advanced pipeline (Photorealistic Profile):
    - general_x4v3 background model (avoids the x4plus oil-painting effect)
    - GFPGAN bypassed (prevents the anime face swap)
    - 10x upscale with synthetic grain
    """
    settings = settings or get_settings()
    
    # Force the photorealistic model instead of the heavy x4plus
    upsampler = get_realesrgan(settings)
    
    bgr = pil_rgb_to_bgr_cv2(pil_im)
    bgr_denoised = _pre_restore_denoise_advanced(bgr, settings)
    
    if settings.advanced_tile <= 0:
        bgr_denoised = _maybe_downscale_bgr(bgr_denoised, settings.max_input_edge)
        
    # BYPASS GFPGAN entirely to preserve 100% authentic face identity
    restored, _ = upsampler.enhance(bgr_denoised, outscale=max(1, int(settings.advanced_upscale_factor)))
        
    # --- The Ultimate Texture Restoration Pass ---
    # The 10x upscale inherently uses a bicubic stretch for the final 2.5x (since the AI is 4x native).
    # This causes a soft/plastic look. We fix this with extreme sharpening and synthetic grain.
    
    # 1. Extreme Micro-Contrast Sharpening (Strong Unsharp Mask)
    gaussian = cv2.GaussianBlur(restored, (0, 0), 3.0)
    restored = cv2.addWeighted(restored, 2.0, gaussian, -1.0, 0)
    
    # 2. Memory-Efficient Synthetic Film Grain
    # Injects micro-texture back into the image so fabric and skin look realistic, not painted.
    h, w = restored.shape[:2]
    noise = np.random.normal(0, 4, (h, w, 1))
    
    noise_pos = np.clip(noise, 0, 255).astype(np.uint8)
    noise_pos = np.repeat(noise_pos, 3, axis=2)
    
    noise_neg = np.clip(-noise, 0, 255).astype(np.uint8)
    noise_neg = np.repeat(noise_neg, 3, axis=2)
    
    restored = cv2.add(restored, noise_pos)
    restored = cv2.subtract(restored, noise_neg)
    
    return bgr_cv2_to_pil_rgb(restored)
