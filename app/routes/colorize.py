from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.api_utils import image_meta, image_to_png_bytes, png_bytes_to_b64, quality_scores_against_input
from app.config import get_settings
from app.services.colorization import run_colorize
from app.utils_upload import read_image_upload

router = APIRouter()


@router.post("/process")
async def process_colorize(file: UploadFile = File(...)) -> StreamingResponse:
    settings = get_settings()
    try:
        img, _fmt = await read_image_upload(file, settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        out, _meta = run_colorize(img, settings)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.post("/process-json")
async def process_colorize_json(file: UploadFile = File(...)) -> JSONResponse:
    settings = get_settings()
    try:
        img, input_fmt = await read_image_upload(file, settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        out, pipe = run_colorize(img, settings)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    input_png = image_to_png_bytes(img)
    output_png = image_to_png_bytes(out)
    payload = {
        "image": png_bytes_to_b64(output_png),
        "meta": {
            "task": "colorize",
            "pipeline": {
                "steps": pipe["pipeline_steps"],
                "model_used": pipe["model_used"],
                "pro_only": pipe["pro_only"],
                "fallback_enabled": pipe["fallback_enabled"],
                "fallback_reason": pipe["fallback_reason"],
                "post_restore": pipe["post_restore"],
                "post_upscale_mode": pipe["post_upscale_mode"],
            },
            "input": image_meta(img, input_png, source_format=input_fmt),
            "output": image_meta(out, output_png, source_format="PNG"),
            "quality": quality_scores_against_input(img, out),
        },
    }
    return JSONResponse(payload)
