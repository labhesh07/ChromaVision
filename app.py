"""
Hugging Face Spaces Entrypoint.
Downloads model weights on startup if missing, then launches the FastAPI app on port 7860.
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

# 1. Download weights programmatically before starting FastAPI
print("Checking for required model weights...")
try:
    from scripts.download_weights import main as download_weights
    download_weights()
except Exception as e:
    print(f"Warning: failed to run download_weights script: {e}")

# 2. Start uvicorn server on port 7860 (Hugging Face default)
import uvicorn
from app.main import app

if __name__ == "__main__":
    print("Starting FastAPI application...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=7860, reload=False)
