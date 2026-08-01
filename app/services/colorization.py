"""Dual-model old image / grayscale colorization service."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from app.config import Settings, get_settings
from app.services.ml_shared import (
    bgr_cv2_to_pil_rgb,
    pil_rgb_to_bgr_cv2,
    run_advanced_upscale,
    run_restore,
    run_upscale,
)

_lock = threading.RLock()
_pro_net = None
_primary_net = None
_fallback_net = None
_pts_cache = None


def _load_pts(path: Path) -> np.ndarray:
    global _pts_cache
    if _pts_cache is not None:
        return _pts_cache
    if not path.is_file():
        raise FileNotFoundError(f"Colorization points file not found at {path}")
    pts = np.load(str(path))
    _pts_cache = pts
    return pts


def _prepare_net(net, pts: np.ndarray) -> None:
    # OpenCV colorization model layer names in Zhang et al. Caffe model.
    class8 = net.getLayerId("class8_ab")
    conv8 = net.getLayerId("conv8_313_rh")
    pts = pts.transpose().reshape(2, 313, 1, 1).astype(np.float32)
    net.getLayer(class8).blobs = [pts]
    net.getLayer(conv8).blobs = [np.full((1, 313), 2.606, dtype=np.float32)]


def _load_caffe_net(prototxt: Path, weights: Path):
    if not prototxt.is_file():
        raise FileNotFoundError(f"Colorization prototxt not found at {prototxt}")
    if not weights.is_file():
        raise FileNotFoundError(f"Colorization model not found at {weights}")
    return cv2.dnn.readNetFromCaffe(str(prototxt), str(weights))


def _get_primary_net(settings: Settings):
    global _primary_net
    with _lock:
        if _primary_net is not None:
            return _primary_net
        pts = _load_pts(settings.colorize_pts)
        net = _load_caffe_net(settings.colorize_prototxt, settings.colorize_primary_weights)
        _prepare_net(net, pts)
        _primary_net = net
        return _primary_net


def _get_fallback_net(settings: Settings):
    global _fallback_net
    with _lock:
        if _fallback_net is not None:
            return _fallback_net
        pts = _load_pts(settings.colorize_pts)
        net = _load_caffe_net(settings.colorize_prototxt, settings.colorize_fallback_weights)
        _prepare_net(net, pts)
        _fallback_net = net
        return _fallback_net


def _get_pro_net(settings: Settings):
    global _pro_net
    with _lock:
        if _pro_net is not None:
            return _pro_net
        pts = _load_pts(settings.colorize_pts)
        candidates = [settings.colorize_primary_weights, settings.colorize_fallback_weights]
        chosen = next((p for p in candidates if p.is_file()), None)
        if chosen is None:
            raise FileNotFoundError(
                "No colorization model found. Expected one of: "
                f"{settings.colorize_primary_weights} or {settings.colorize_fallback_weights}"
            )
        net = _load_caffe_net(settings.colorize_prototxt, chosen)
        _prepare_net(net, pts)
        _pro_net = net
        return _pro_net


def _colorize_with_net(bgr_u8: np.ndarray, net) -> np.ndarray:
    bgr = bgr_u8.astype(np.float32) / 255.0
    h, w = bgr.shape[:2]
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l = lab[:, :, 0]

    l_rs = cv2.resize(l, (224, 224))
    l_rs -= 50.0

    net.setInput(cv2.dnn.blobFromImage(l_rs))
    ab = net.forward()[0, :, :, :].transpose((1, 2, 0))
    ab = cv2.resize(ab, (w, h))

    lab_out = np.concatenate((l[:, :, np.newaxis], ab), axis=2)
    bgr_out = cv2.cvtColor(lab_out, cv2.COLOR_LAB2BGR)
    bgr_out = np.clip(bgr_out, 0, 1)
    return np.round(bgr_out * 255.0).astype(np.uint8)


def _fallback_classical(bgr_u8: np.ndarray) -> np.ndarray:
    # Deterministic classical fallback if model loading fails:
    # apply soft sepia-like chroma curve on luminance.
    gray = cv2.cvtColor(bgr_u8, cv2.COLOR_BGR2GRAY)
    eq = cv2.equalizeHist(gray)
    tone = cv2.applyColorMap(eq, cv2.COLORMAP_BONE)
    mix = cv2.addWeighted(bgr_u8, 0.35, tone, 0.65, 0)
    return mix


def run_colorize(pil_im: Image.Image, settings: Settings | None = None, apply_upscale: bool = True) -> tuple[Image.Image, dict[str, Any]]:
    """
    Run separate colorization feature with primary+fallback model strategy.
    Returns (output_image, metadata).
    """
    settings = settings or get_settings()
    bgr = pil_rgb_to_bgr_cv2(pil_im)
    steps = ["Input", "Colorization model"]
    fallback_reason = ""
    model_used = "pro_model"

    if settings.colorize_pro_only:
        # Pro-only path: use high-quality model branch and skip primary branch entirely.
        try:
            net = _get_pro_net(settings)
            out_bgr = _colorize_with_net(bgr, net)
            steps[1] = "Pro colorization model"
        except Exception as e:
            raise RuntimeError(f"Pro colorization model failed: {e}") from e
    elif settings.colorize_force_fallback:
        try:
            net = _get_fallback_net(settings)
            out_bgr = _colorize_with_net(bgr, net)
            model_used = "fallback"
            steps[1] = "Fallback colorization model (forced)"
        except Exception:
            out_bgr = _fallback_classical(bgr)
            model_used = "fallback_classical"
            steps[1] = "Classical fallback colorization"
            fallback_reason = "Forced fallback model unavailable."
    else:
        try:
            net = _get_primary_net(settings)
            out_bgr = _colorize_with_net(bgr, net)
        except Exception as e_primary:
            if not settings.colorize_fallback_enabled:
                raise RuntimeError(f"Primary colorization failed: {e_primary}") from e_primary
            fallback_reason = str(e_primary)
            try:
                net = _get_fallback_net(settings)
                out_bgr = _colorize_with_net(bgr, net)
                model_used = "fallback"
                steps[1] = "Fallback colorization model"
            except Exception:
                out_bgr = _fallback_classical(bgr)
                model_used = "fallback_classical"
                steps[1] = "Classical fallback colorization"

    out_pil = bgr_cv2_to_pil_rgb(out_bgr)

    if settings.colorize_apply_restore:
        out_pil = run_restore(out_pil, settings)
        steps.append("GFPGAN/Real-ESRGAN restore")

    if apply_upscale:
        mode = settings.colorize_post_upscale_mode.strip().lower()
        if mode == "upscale":
            out_pil = run_upscale(out_pil, settings)
            steps.append("Real-ESRGAN upscale")
        elif mode == "advanced":
            # Prevent OOM: cap input size before the massive 10x upscale.
            # A 1200px edge * 10x = 12,000px final edge. 
            # Anything larger causes NumPy/OpenCV OOM during the texture injection pass.
            w, h = out_pil.size
            max_dim = 1200
            if max(w, h) > max_dim:
                ratio = max_dim / float(max(w, h))
                new_w = int(w * ratio)
                new_h = int(h * ratio)
                out_pil = out_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
                steps.append(f"OOM Prevention Resize ({w}x{h} -> {new_w}x{new_h})")
                
            out_pil = run_advanced_upscale(out_pil, settings)
            steps.append("Advanced 10x upscale")
    else:
        mode = "none"

    steps.append("Output")
    meta = {
        "model_used": model_used,
        "pro_only": bool(settings.colorize_pro_only),
        "fallback_enabled": bool(settings.colorize_fallback_enabled),
        "fallback_reason": fallback_reason,
        "pipeline_steps": steps,
        "post_restore": bool(settings.colorize_apply_restore),
        "post_upscale_mode": mode,
    }
    return out_pil, meta
