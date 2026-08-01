from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.api_utils import image_meta, image_to_png_bytes, png_bytes_to_b64, quality_scores_against_input
from app.config import get_settings
from app.services.ml_shared import run_advanced_upscale
from app.utils_upload import read_image_upload

router = APIRouter()


@router.post("/process")
async def process_advanced_upscale(file: UploadFile = File(...)) -> StreamingResponse:
    settings = get_settings()
    try:
        img, _fmt = await read_image_upload(file, settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        out = run_advanced_upscale(img, settings)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Inference failed (GPU memory?): {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.post("/process-json")
async def process_advanced_upscale_json(file: UploadFile = File(...)) -> JSONResponse:
    settings = get_settings()
    try:
        img, input_fmt = await read_image_upload(file, settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        out = run_advanced_upscale(img, settings)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Inference failed (GPU memory?): {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    input_png = image_to_png_bytes(img)
    output_png = image_to_png_bytes(out)
    payload = {
        "image": png_bytes_to_b64(output_png),
        "meta": {
            "task": "advanced_upscale",
            "pipeline": {
                "steps": [
                    "Input",
                    "RealESRGAN Photorealistic 10x Upscale",
                    "Micro-Contrast Texture Pass",
                    "Synthetic Film Grain Injection",
                    "Output",
                ],
                "model": "RealESRGAN (Photorealistic Profile)",
                "denoise": bool(settings.advanced_denoise),
                "tile": int(settings.advanced_tile),
                "aligned_upscale_factor": int(settings.advanced_upscale_factor),
            },
            "input": image_meta(img, input_png, source_format=input_fmt),
            "output": image_meta(out, output_png, source_format="PNG"),
            "quality": quality_scores_against_input(img, out),
        },
    }
    return JSONResponse(payload)
