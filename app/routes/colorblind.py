from io import BytesIO
from itertools import combinations
from typing import cast

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.color import deltaE_ciede2000, rgb2lab

from app.api_utils import channel_histogram, image_meta, image_to_png_bytes, png_bytes_to_b64
from app.config import get_settings
from app.services import colorblind as cb
from app.services.colorblind import CvdType, Mode
from app.utils_upload import read_image_upload

router = APIRouter()


def _validate_colorblind_params(mode: str, cvd_type: str, severity: float, strength: float) -> tuple[str, str, float, float]:
    if mode not in ("simulate", "daltonize"):
        raise HTTPException(status_code=400, detail="mode must be simulate or daltonize")
    if cvd_type not in (
        "protanopia",
        "deuteranopia",
        "tritanopia",
        "protanomaly",
        "deuteranomaly",
        "tritanomaly",
    ):
        raise HTTPException(status_code=400, detail="Invalid cvd_type")
    # 0 = normal, 1 = full Machado severity (internally 0–100)
    severity = max(0.0, min(1.0, float(severity)))
    strength = max(0.0, min(3.0, float(strength)))
    return mode, cvd_type, severity, strength


def _run_colorblind(img, mode: str, cvd_type: str, severity: float, strength: float):
    return cb.process_image(
        img,
        mode=cast(Mode, mode),
        cvd_type=cast(CvdType, cvd_type),
        severity=severity,
        strength=strength,
    )


def _hex_from_rgb(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _simulate_palette_rgb(rgb: tuple[int, int, int], cvd_type: CvdType, severity: float) -> tuple[int, int, int]:
    arr = np.array([[list(rgb)]], dtype=np.uint8)
    arrf = arr.astype(np.float64) / 255.0
    out = cb.simulate_cvd(arrf, cvd_type, severity)
    out_u8 = np.round(np.clip(out, 0.0, 1.0) * 255.0).astype(np.uint8)
    return tuple(int(x) for x in out_u8[0, 0, :3])


def _dominant_palette(image: Image.Image, n_colors: int = 6) -> list[tuple[int, int, int]]:
    # PIL adaptive palette is deterministic and lightweight for API usage.
    pal = image.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=n_colors).convert("RGB")
    arr = np.asarray(pal, dtype=np.uint8).reshape(-1, 3)
    uniq, counts = np.unique(arr, axis=0, return_counts=True)
    order = np.argsort(-counts)
    return [tuple(int(v) for v in uniq[i]) for i in order[:n_colors]]


def _pair_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    v1 = np.array(c1, dtype=np.float64)
    v2 = np.array(c2, dtype=np.float64)
    return float(np.linalg.norm(v1 - v2))


def _deltae(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    arr = np.array([[list(c1), list(c2)]], dtype=np.uint8).astype(np.float64) / 255.0
    lab = rgb2lab(arr)
    de = deltaE_ciede2000(lab[0, 0], lab[0, 1])
    return float(de)


def _risk_class(deltae: float) -> str:
    # Lower DeltaE means colors become less distinguishable.
    if deltae < 10.0:
        return "risky"
    if deltae < 20.0:
        return "warning"
    return "safe"


def _build_cvd_grid(image: Image.Image) -> Image.Image:
    variants: list[tuple[str, Image.Image]] = [("Original", image.convert("RGB"))]
    cvd_specs: list[tuple[str, CvdType, float]] = [
        ("Protanomaly 50%", "protanopia", 0.5),
        ("Protanopia 100%", "protanopia", 1.0),
        ("Deuteranomaly 50%", "deuteranopia", 0.5),
        ("Deuteranopia 100%", "deuteranopia", 1.0),
        ("Tritanomaly 50%", "tritanopia", 0.5),
        ("Tritanopia 100%", "tritanopia", 1.0),
        ("Protanomaly 80%", "protanopia", 0.8),
        ("Deuteranomaly 80%", "deuteranopia", 0.8),
    ]
    for label, ctype, sev in cvd_specs:
        out = cb.process_image(image, mode="simulate", cvd_type=ctype, severity=sev, strength=1.0)
        variants.append((label, out))

    src_w, src_h = image.size
    max_edge = 360
    scale = min(1.0, max_edge / float(max(src_w, src_h)))
    thumb_w = max(64, int(round(src_w * scale)))
    thumb_h = max(64, int(round(src_h * scale)))
    caption_h = 34
    cell_w = thumb_w
    cell_h = thumb_h + caption_h
    canvas = Image.new("RGB", (cell_w * 3, cell_h * 3), (18, 26, 37))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    for idx, (label, variant) in enumerate(variants):
        row = idx // 3
        col = idx % 3
        x = col * cell_w
        y = row * cell_h
        canvas.paste(variant.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS), (x, y))
        draw.rectangle((x, y + thumb_h, x + cell_w, y + cell_h), fill=(28, 38, 54))
        draw.text((x + 8, y + thumb_h + 10), label, fill=(230, 238, 245), font=font)
    return canvas


@router.post("/process")
async def process_colorblind(
    file: UploadFile = File(...),
    mode: str = Form(...),
    cvd_type: str = Form("deuteranopia"),
    severity: float = Form(1.0),
    strength: float = Form(1.0),
) -> StreamingResponse:
    settings = get_settings()
    mode, cvd_type, severity, strength = _validate_colorblind_params(mode, cvd_type, severity, strength)

    try:
        img, _fmt = await read_image_upload(file, settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        out = _run_colorblind(img, mode, cvd_type, severity, strength)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}") from e

    buf = BytesIO()
    out.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@router.post("/process-json")
async def process_colorblind_json(
    file: UploadFile = File(...),
    mode: str = Form(...),
    cvd_type: str = Form("deuteranopia"),
    severity: float = Form(1.0),
    strength: float = Form(1.0),
) -> JSONResponse:
    settings = get_settings()
    mode, cvd_type, severity, strength = _validate_colorblind_params(mode, cvd_type, severity, strength)

    try:
        img, input_fmt = await read_image_upload(file, settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        out = _run_colorblind(img, mode, cvd_type, severity, strength)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}") from e

    input_png = image_to_png_bytes(img)
    output_png = image_to_png_bytes(out)
    payload = {
        "image": png_bytes_to_b64(output_png),
        "meta": {
            "task": "colorblind",
            "params": {
                "mode": mode,
                "cvd_type": cvd_type,
                "severity": severity,
                "strength": strength,
            },
            "input": image_meta(img, input_png, source_format=input_fmt),
            "output": image_meta(out, output_png, source_format="PNG"),
        },
    }
    return JSONResponse(payload)


@router.post("/histogram")
async def colorblind_histogram(
    file: UploadFile = File(...),
    mode: str = Form("simulate"),
    cvd_type: str = Form("deuteranopia"),
    severity: float = Form(1.0),
    strength: float = Form(1.0),
) -> JSONResponse:
    settings = get_settings()
    mode, cvd_type, severity, strength = _validate_colorblind_params(mode, cvd_type, severity, strength)

    try:
        img, _fmt = await read_image_upload(file, settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        out = _run_colorblind(img, mode, cvd_type, severity, strength)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}") from e

    in_hist = channel_histogram(img)
    out_hist = channel_histogram(out)
    diff = {k: [int(out_hist[k][i] - in_hist[k][i]) for i in range(256)] for k in ("r", "g", "b")}
    return JSONResponse(
        {
            "input_histogram": in_hist,
            "output_histogram": out_hist,
            "difference_histogram": diff,
            "params": {
                "mode": mode,
                "cvd_type": cvd_type,
                "severity": severity,
                "strength": strength,
            },
        }
    )


@router.post("/grid")
async def colorblind_grid(file: UploadFile = File(...)) -> JSONResponse:
    settings = get_settings()
    try:
        img, input_fmt = await read_image_upload(file, settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    grid_img = _build_cvd_grid(img)
    grid_png = image_to_png_bytes(grid_img)
    return JSONResponse(
        {
            "image": png_bytes_to_b64(grid_png),
            "meta": {
                "task": "colorblind_grid",
                "input_format": input_fmt,
                "grid_size": {"width": grid_img.width, "height": grid_img.height},
                "description": "Original plus 8 CVD simulations in 3x3 grid",
            },
        }
    )


@router.post("/palette-safety")
async def colorblind_palette_safety(file: UploadFile = File(...)) -> JSONResponse:
    settings = get_settings()
    try:
        img, _fmt = await read_image_upload(file, settings)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    palette = _dominant_palette(img, n_colors=6)
    cvd_types: list[CvdType] = [
        "protanopia",
        "deuteranopia",
        "tritanopia",
        "protanomaly",
        "deuteranomaly",
        "tritanomaly",
    ]
    risk_threshold_legacy = 24.0

    pair_reports = []
    overall_risky_pairs = set()
    warning_pairs = set()
    for i, j in combinations(range(len(palette)), 2):
        base_dist = _pair_distance(palette[i], palette[j])  # legacy field
        base_deltae = _deltae(palette[i], palette[j])
        per_type = {}
        risky = False
        warning = False
        for t in cvd_types:
            c1 = _simulate_palette_rgb(palette[i], t, 1.0)
            c2 = _simulate_palette_rgb(palette[j], t, 1.0)
            rgb_d = _pair_distance(c1, c2)
            de = _deltae(c1, c2)
            cls = _risk_class(de)
            risk = cls == "risky"
            warning = warning or cls == "warning"
            per_type[t] = {
                "simulated_distance": round(rgb_d, 2),  # legacy compatibility
                "deltae": round(de, 2),
                "risk_class": cls,
                "risky": risk,
            }
            risky = risky or risk
        if risky:
            overall_risky_pairs.add((i, j))
        elif warning:
            warning_pairs.add((i, j))
        pair_reports.append(
            {
                "pair": [i, j],
                "base_distance": round(base_dist, 2),  # legacy compatibility
                "base_deltae": round(base_deltae, 2),
                "per_cvd": per_type,
                "risky_any": risky,
                "warning_any": warning and not risky,
            }
        )

    palette_json = [{"index": i, "rgb": list(c), "hex": _hex_from_rgb(c)} for i, c in enumerate(palette)]
    return JSONResponse(
        {
            "palette": palette_json,
            "pairs": pair_reports,
            "summary": {
                "risky_pair_count": len(overall_risky_pairs),
                "warning_pair_count": len(warning_pairs),
                "total_pairs": len(pair_reports),
                "threshold": risk_threshold_legacy,  # legacy UI compatibility
                "metric": "CIEDE2000 DeltaE",
                "risk_thresholds": {"risky_lt": 10.0, "warning_lt": 20.0},
                "guidance": "Lower DeltaE means lower perceptual separability after CVD simulation.",
            },
        }
    )
