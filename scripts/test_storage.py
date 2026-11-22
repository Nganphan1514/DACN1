import os
import sys
import tempfile

import cv2
import numpy as np
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.storage_service import is_storage_configured, upload_snapshot_to_supabase


def main():
    if not is_storage_configured():
        print("LOI: Chua cau hinh SUPABASE_URL hoac SUPABASE_SERVICE_KEY trong .env!")
        sys.exit(1)

    # Tao 1 anh JPEG test nho co chu DACN1 OK
    img = np.zeros((160, 360, 3), dtype=np.uint8)
    img[:] = (30, 20, 15)
    cv2.putText(img, "DACN1 SUPABASE OK!", (25, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 180), 2)

    tmp_path = os.path.join(tempfile.gettempdir(), "dacn1_storage_test.jpg")
    cv2.imwrite(tmp_path, img)

    try:
        url = upload_snapshot_to_supabase(tmp_path)
        print("Ket qua upload:", url)

        if not str(url).startswith("https://"):
            print("THAT BAI: Khong upload duoc len Supabase Storage (fallback local).")
            sys.exit(1)

        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            print(f"THANH CONG 100%! Anh public truy cap duoc (HTTP 200, {len(resp.content)} bytes).")
            print("Mo link nay tren trinh duyet de xem anh:", url)
        else:
            print(f"Da upload nhung chua doc public duoc (HTTP {resp.status_code}). Hay kiem tra bucket 'snapshots' da bat Public bucket chua!")
            sys.exit(1)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    main()
