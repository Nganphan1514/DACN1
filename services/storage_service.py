import os
import requests

from config.app_config import (
    SUPABASE_BUCKET_PRIVATE,
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


def create_signed_url(filename, expires_in=3600):
    """
    Tao Signed URL co thoi han (mac dinh 1 gio) cho Supabase Private Bucket (P0-5: SEC-01).
    """
    if not is_storage_configured():
        return None
    safe_name = os.path.basename(str(filename))
    sign_url = f"{SUPABASE_URL}/storage/v1/object/sign/{SUPABASE_SNAPSHOT_BUCKET}/{safe_name}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(sign_url, headers=headers, json={"expiresIn": int(expires_in)}, timeout=8)
        if resp.status_code == 200:
            signed_path = resp.json().get("signedURL") or resp.json().get("signedUrl")
            if signed_path:
                if signed_path.startswith("http"):
                    return signed_path
                if not signed_path.startswith("/storage/v1"):
                    signed_path = f"/storage/v1{signed_path}"
                return f"{SUPABASE_URL}{signed_path}"
    except Exception as e:
        logger.warning("Create signed URL error: %s", e)
    return None


def resolve_snapshot_url(stored_path):
    """
    Chuan hoa duong dan anh luu trong DB thanh URL hien thi duoc tren Web & App Expo.
    Neu SUPABASE_BUCKET_PRIVATE=true thi tu dong tao Signed URL co thoi han.
    """
    if not stored_path:
        return None
    text = str(stored_path).strip()
    if text.startswith(("http://", "https://")):
        if SUPABASE_BUCKET_PRIVATE and SUPABASE_URL and text.startswith(SUPABASE_URL):
            signed = create_signed_url(os.path.basename(text))
            if signed:
                return signed
        return text
    return f"/api/snapshots/{os.path.basename(text)}"
