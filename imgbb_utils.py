import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")


def upload_file_to_imgbb(file_bytes: bytes, filename: str) -> str:
    """Faylni ImgBB ga yuklab, havolasini qaytaradi."""
    if not IMGBB_API_KEY:
        raise Exception("IMGBB API key topilmadi. .env faylni tekshiring.")

    # ImgBB API image param needs base64 string
    image_b64 = base64.b64encode(file_bytes).decode("utf-8")
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": IMGBB_API_KEY,
        "image": image_b64,
        "name": filename,
    }

    resp = requests.post(url, data=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        # Agar API xato qaytarsa
        error_msg = data.get("error", {}).get("message") if isinstance(data.get("error"), dict) else None
        raise Exception(error_msg or "ImgBB upload xatosi")

    # display_url mavjud bo'ladi
    return data["data"].get("display_url") or data["data"].get("url")