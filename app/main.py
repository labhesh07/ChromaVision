"""FastAPI entrypoint."""

from pathlib import Path

from app.torchvision_shim import apply_torchvision_shim

apply_torchvision_shim()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routes import advanced_upscale, colorblind, colorize, index, restore, upscale

settings = get_settings()
app = FastAPI(title="ChromaVision", description="AI-powered image processing: CVD, restoration, and upscaling")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(index.router)
app.include_router(colorblind.router, prefix="/colorblind", tags=["colorblind"])
app.include_router(colorize.router, prefix="/colorize", tags=["colorize"])
app.include_router(restore.router, prefix="/restore", tags=["restore"])
app.include_router(upscale.router, prefix="/upscale", tags=["upscale"])
app.include_router(advanced_upscale.router, prefix="/advanced-upscale", tags=["advanced-upscale"])
