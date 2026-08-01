"""Application settings loaded from environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    max_upload_mb: int = 20
    device: str = "cuda"  # cuda or cpu

    # Project root (parent of app/)
    base_dir: Path = Path(__file__).resolve().parent.parent
    weights_dir: Path = base_dir / "weights"

    realesrgan_weights: Path = weights_dir / "realesr-general-x4v3.pth"
    realesrgan_x4plus_weights: Path = weights_dir / "RealESRGAN_x4plus.pth"
    gfpgan_weights: Path = weights_dir / "GFPGANv1.4.pth"

    # Legacy pre-downscale before ML inference if larger (0 disables cap).
    max_input_edge: int = 2048

    # Real-ESRGAN model profile:
    # - "general_x4v3": lightweight SRVGG (faster)
    # - "x4plus": RRDBNet (higher quality, heavier)
    realesrgan_model: str = "general_x4v3"
    realesrgan_tile: int = 400
    realesrgan_tile_pad: int = 10
    realesrgan_pre_pad: int = 0

    # Restore pipeline controls
    restore_upscale: int = 2
    restore_denoise: bool = True
    denoise_strength: int = 7
    denoise_color_strength: int = 7

    # Separate advanced upscale/restore pipeline (pro-quality profile)
    advanced_upscale_factor: int = 10
    advanced_tile: int = 400
    advanced_tile_pad: int = 10
    advanced_pre_pad: int = 0
    advanced_denoise: bool = False
    advanced_denoise_strength: int = 0
    advanced_denoise_color_strength: int = 0 

    # Colorization (separate pro feature with primary + fallback models)
    colorize_prototxt: Path = weights_dir / "colorization_deploy_v2.prototxt"
    colorize_primary_weights: Path = weights_dir / "colorization_release_v2.caffemodel"
    colorize_fallback_weights: Path = weights_dir / "colorization_release_v2_norebal.caffemodel"
    colorize_pts: Path = weights_dir / "pts_in_hull.npy"
    colorize_fallback_enabled: bool = True
    colorize_force_fallback: bool = False
    colorize_pro_only: bool = True

    # Optional post-enhancement chain after colorization
    colorize_apply_restore: bool = True
    # none | upscale | advanced
    colorize_post_upscale_mode: str = "advanced"


@lru_cache
def get_settings() -> Settings:
    return Settings()
