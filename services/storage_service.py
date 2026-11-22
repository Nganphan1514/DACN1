import os
import requests

from config.app_config import (
    SUPABASE_SERVICE_KEY,
    SUPABASE_SNAPSHOT_BUCKET,
    SUPABASE_URL,
)
from config.logger import get_logger

logger = get_logger("storage_service")


def is_storage_configured():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return False
    if "YOUR_PROJECT_REF" in SUPABASE_URL:
        return False
    return True


def build_public_url(filename):
    safe_name = os.path.basename(str(filename))
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_SNAPSHOT_BUCKET}/{safe_name}"


def upload_snapshot_to_supabase(local_file_path):
    """
    Upload anh snapshot cuc bo len Supabase Storage bucket (cong khai).
    - Thanh cong: tra ve public HTTPS URL de luu vao DB va hien thi tren Web/App Expo.
    - Chua cau hinh hoac mat mang: fallback tra ve duong dan cuc bo (khong lam gian doan AI).
    """
    if not local_file_path or not os.path.isfile(local_file_path):
        return local_file_path

    if not is_storage_configured():
        return local_file_path

    filename = os.path.basename(local_file_path)
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_SNAPSHOT_BUCKET}/{filename}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
        "Content-Type": "image/jpeg",
        "x-upsert": "true",
    }

    try:
        with open(local_file_path, "rb") as f:
            data = f.read()

        resp = requests.post(upload_url, headers=headers, data=data, timeout=10)
        if resp.status_code in (200, 201):
            public_url = build_public_url(filename)
            logger.info("Uploaded snapshot to Supabase Storage: %s", public_url)
            return public_url

        logger.warning(
            "Supabase Storage upload failed (HTTP %s): %s",
            resp.status_code,
            resp.text[:200],
        )
        return local_file_path

    except Exception as e:
        logger.warning("Supabase Storage upload error (fallback local): %s", e)
        return local_file_path


def resolve_snapshot_url(stored_path):
    """
    Chuan hoa duong dan anh luu trong DB thanh URL hien thi duoc tren Web & App Expo.
    """
    if not stored_path:
        return None
    text = str(stored_path).strip()
    if text.startswith(("http://", "https://")):
        return text
    return f"/api/snapshots/{os.path.basename(text)}"
