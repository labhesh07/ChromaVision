"""
Download Real-ESRGAN and GFPGAN weights into ./weights/

Run from project root:
  python scripts/download_weights.py
"""

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEIGHTS = ROOT / "weights"

URLS = {
    "realesr-general-x4v3.pth": (
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth"
    ),
    "RealESRGAN_x4plus.pth": (
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
    ),
    "GFPGANv1.4.pth": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
    "colorization_deploy_v2.prototxt": (
        "https://raw.githubusercontent.com/richzhang/colorization/caffe/models/colorization_deploy_v2.prototxt"
    ),
    "pts_in_hull.npy": (
        "https://raw.githubusercontent.com/richzhang/colorization/caffe/resources/pts_in_hull.npy"
    ),
    "colorization_release_v2.caffemodel": (
        "https://github.com/spmallick/learnopencv/releases/download/Colorization/colorization_release_v2.caffemodel"
    ),
    "colorization_release_v2_norebal.caffemodel": (
        "https://people.eecs.berkeley.edu/~rich.zhang/projects/2016_colorization/files/demo_v2/colorization_release_v2_norebal.caffemodel"
    ),
}


def download_url(url: str, dest: Path) -> None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req) as response, open(dest, "wb") as out_file:
        chunk_size = 1024 * 1024  # 1MB
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)


def main() -> None:
    WEIGHTS.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        dest = WEIGHTS / name
        if dest.is_file():
            print(f"Skip (exists): {dest}")
            continue
        print(f"Downloading {name} …")
        try:
            download_url(url, dest)
            print(f"Saved {dest}")
        except Exception as e:
            print(f"Warning: failed to download {name}: {e}")


if __name__ == "__main__":
    main()
