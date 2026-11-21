import math
import os
import sys
import threading
import time

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.location_config import DEMO_LOCATION


CACHE_TTL_SECONDS = 600  # 10 phut

_cache_lock = threading.Lock()
_cached_key = None
_cached_rest_stop = None
_cached_at = 0.0
_fetch_in_progress = False


def get_current_location():
    return (DEMO_LOCATION["lat"], DEMO_LOCATION["lng"])


def calculate_distance(lat1, lng1, lat2, lng2):
    R = 6371

    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _location_key(lat, lng):
    return (round(lat, 3), round(lng, 3))


def find_nearest_rest_stop():
    """
    Tim diem dung nghi gan nhat (dong bo). Co ket hop cache theo toa do.
    """
    global _cached_key, _cached_rest_stop, _cached_at

    lat, lng = get_current_location()
    key = _location_key(lat, lng)
    now = time.time()

    with _cache_lock:
        if (
            _cached_key == key
            and _cached_rest_stop is not None
            and (now - _cached_at) < CACHE_TTL_SECONDS
        ):
            return _cached_rest_stop

    try:
        headers = {"User-Agent": "DACN1 Driver System"}
        keywords = [
            "fuel station",
            "petrol station",
            "cafe",
            "rest area",
        ]

        for keyword in keywords:
            try:
                url = "https://nominatim.openstreetmap.org/search"
                params = {
                    "q": keyword,
                    "format": "json",
                    "limit": 5,
                    "viewbox": f"{lng-0.03},{lat+0.03},{lng+0.03},{lat-0.03}",
                    "bounded": 1,
                }

                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=5,
                )

                data = response.json()
                if not data:
                    continue

                nearest = None
                min_distance = float("inf")

                for place in data:
                    place_lat = float(place["lat"])
                    place_lng = float(place["lon"])
                    distance = calculate_distance(lat, lng, place_lat, place_lng)

                    if distance < min_distance:
                        min_distance = distance
                        nearest = place

                if nearest:
                    result = {
                        "name": nearest.get("display_name", keyword),
                        "distance_km": round(min_distance, 2),
                    }
                    with _cache_lock:
                        _cached_key = key
                        _cached_rest_stop = result
                        _cached_at = time.time()
                    return result

            except Exception:
                continue

        return None

    except Exception as e:
        print("Location error:", e)
        return None


def _background_fetch_worker():
    global _fetch_in_progress
    try:
        find_nearest_rest_stop()
    finally:
        with _cache_lock:
            _fetch_in_progress = False


def prefetch_nearest_rest_stop_async():
    """
    Kich hoat tim diem dung nghi o luong nen (khong chan camera).
    """
    global _fetch_in_progress

    lat, lng = get_current_location()
    key = _location_key(lat, lng)
    now = time.time()

    with _cache_lock:
        cache_valid = (
            _cached_key == key
            and _cached_rest_stop is not None
            and (now - _cached_at) < CACHE_TTL_SECONDS
        )
        if cache_valid or _fetch_in_progress:
            return
        _fetch_in_progress = True

    thread = threading.Thread(target=_background_fetch_worker, daemon=True)
    thread.start()


def get_cached_rest_stop():
    """
    Tra ve ngay ket qua diem dung trong cache (khong block).
    Neu cache rong hoac het han thi tu dong goi tai nen cho lan sau.
    """
    prefetch_nearest_rest_stop_async()
    with _cache_lock:
        return _cached_rest_stop


if __name__ == "__main__":
    vi_tri = get_current_location()
    print("Vi tri:", vi_tri)
    nearest = find_nearest_rest_stop()
    print("Gan nhat:", nearest)
