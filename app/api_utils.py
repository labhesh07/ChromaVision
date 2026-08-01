"""Utilities for JSON API image responses and quality metrics."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


def image_to_png_bytes(image: Image.Image) -> bytes:
    """Encode PIL image as optimized PNG bytes."""
    buf = BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def image_meta(image: Image.Image, png_bytes: bytes, source_format: str | None = None) -> dict[str, Any]:
    return {
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "format": source_format or "PNG",
        "byte_size": len(png_bytes),
    }


def png_bytes_to_b64(png_bytes: bytes) -> str:
    return base64.b64encode(png_bytes).decode("ascii")


def quality_scores_against_input(input_image: Image.Image, output_image: Image.Image) -> dict[str, Any]:
    """
    Compute SSIM/PSNR using input as reference.
    If dimensions differ (e.g. upscale), output is resized to input dimensions.
    """
    in_rgb = input_image.convert("RGB")
    out_rgb = output_image.convert("RGB")
    resized = False
    if in_rgb.size != out_rgb.size:
        out_rgb = out_rgb.resize(in_rgb.size, Image.Resampling.LANCZOS)
        resized = True

    ref = np.asarray(in_rgb, dtype=np.uint8)
    pred = np.asarray(out_rgb, dtype=np.uint8)

    ssim = structural_similarity(ref, pred, channel_axis=2, data_range=255)
    psnr = peak_signal_noise_ratio(ref, pred, data_range=255)

    return {
        "ssim": float(ssim),
        "psnr": float(psnr),
        "aligned_to_input_size": resized,
        "reference_size": {"width": in_rgb.width, "height": in_rgb.height},
    }


def channel_histogram(image: Image.Image) -> dict[str, list[int]]:
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    out: dict[str, list[int]] = {}
    for idx, key in enumerate(("r", "g", "b")):
        hist, _ = np.histogram(rgb[..., idx], bins=256, range=(0, 256))
        out[key] = hist.astype(int).tolist()
    return out
