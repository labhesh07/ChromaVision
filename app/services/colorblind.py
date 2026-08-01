"""Color vision deficiency simulation and simple daltonization."""

from typing import Literal

import numpy as np
from colorspacious import cspace_convert
from PIL import Image

CvdType = Literal[
    "protanopia",
    "deuteranopia",
    "tritanopia",
    "protanomaly",
    "deuteranomaly",
    "tritanomaly",
]
Mode = Literal["simulate", "daltonize"]

# Map all supported names to colorspacious anomaly types.
_CVD_ANOMALY_MAP: dict[CvdType, str] = {
    "protanopia": "protanomaly",
    "deuteranopia": "deuteranomaly",
    "tritanopia": "tritanomaly",
    "protanomaly": "protanomaly",
    "deuteranomaly": "deuteranomaly",
    "tritanomaly": "tritanomaly",
}


def _srgb255_to_unit01(arr: np.ndarray) -> np.ndarray:
    return (arr.astype(np.float64) / 255.0).clip(0.0, 1.0)


def _unit01_to_srgb255(arr: np.ndarray) -> np.ndarray:
    return np.round(np.clip(arr, 0.0, 1.0) * 255.0).astype(np.uint8)


def _effective_severity100(cvd_type: CvdType, severity01: float) -> float:
    """
    Distinguish anomaly vs opia in a way compatible with colorspacious.
    - opia types can reach full Machado severity (0..100).
    - anomaly types are capped lower to remain milder than complete cone absence.
    """
    sev = float(np.clip(severity01, 0.0, 1.0))
    if cvd_type.endswith("anomaly"):
        return sev * 80.0
    return sev * 100.0


def simulate_cvd(rgb: np.ndarray, cvd_type: CvdType, severity: float) -> np.ndarray:
    """rgb: float64 (H,W,3) unit sRGB. severity is 0..1, mapped to Machado 0..100."""
    h, w, _ = rgb.shape
    flat = rgb.reshape(-1, 3)
    sev100 = _effective_severity100(cvd_type, severity)
    end_space = {
        "name": "sRGB1+CVD",
        "cvd_type": _CVD_ANOMALY_MAP[cvd_type],
        "severity": sev100,
    }
    out = cspace_convert(flat, "sRGB1", end_space)
    return out.reshape(h, w, 3).astype(np.float64)


def daltonize(rgb: np.ndarray, cvd_type: CvdType, severity: float, strength: float) -> np.ndarray:
    """
    Push colors away from the simulated-CVD appearance so contrasts lost for that deficiency
    are partially restored. strength in [0, 2] typical.
    """
    sim = simulate_cvd(rgb, cvd_type, severity)
    delta = rgb - sim
    out = rgb + float(strength) * delta
    return np.clip(out, 0.0, 1.0)


def process_image(
    image: Image.Image,
    mode: Mode,
    cvd_type: CvdType,
    severity: float,
    strength: float,
) -> Image.Image:
    """Run CVD pipeline; returns RGB PIL image."""
    arr = _srgb255_to_unit01(np.asarray(image))
    if mode == "simulate":
        out = simulate_cvd(arr, cvd_type, severity)
    else:
        out = daltonize(arr, cvd_type, severity, strength)
    out_u8 = _unit01_to_srgb255(out)
    return Image.fromarray(out_u8, mode="RGB")
