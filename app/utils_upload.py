"""Validate and read uploaded image bytes."""

from io import BytesIO

from fastapi import HTTPException, UploadFile
import pillow_avif  # MUST import to enable AVIF support in PIL
from PIL import Image, UnidentifiedImageError

from app.config import Settings


async def read_image_upload(file: UploadFile, settings: Settings) -> tuple[Image.Image, str]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")
    content_type = (file.content_type or "").lower()
    if content_type not in ("image/jpeg", "image/png", "image/webp", "image/avif", "image/jpg", ""):
        if not file.filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".avif")):
            raise HTTPException(status_code=400, detail="Use JPEG, PNG, WebP, or AVIF")

    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {settings.max_upload_mb} MB)",
        )
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        img = Image.open(BytesIO(data))
        img.load()
    except UnidentifiedImageError as e:
        raise HTTPException(status_code=400, detail="Invalid image file") from e

    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Prevent OOM by strictly limiting maximum dimensions
    # MAX_DIMENSION = 4096
    # if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
    #     # Calculate new dimensions preserving aspect ratio
    #     ratio = min(MAX_DIMENSION / img.width, MAX_DIMENSION / img.height)
    #     new_w = int(img.width * ratio)
    #     new_h = int(img.height * ratio)
    #     img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    fmt = (img.format or "PNG").upper()
    return img, fmt
