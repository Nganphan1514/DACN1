import requests
import math
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.location_config import DEMO_LOCATION


# ==========================
# GET CURRENT LOCATION
# ==========================
def get_current_location():

    return (DEMO_LOCATION["lat"], DEMO_LOCATION["lng"])


# ==========================
# DISTANCE
# ==========================
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


# ==========================
# FIND NEAREST REST STOP
# ==========================
def find_nearest_rest_stop():

    try:

        lat, lng = get_current_location()

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
                    # vùng gần Đà Nẵng
                    "viewbox": f"{lng-0.03},"
                    f"{lat+0.03},"
                    f"{lng+0.03},"
                    f"{lat-0.03}",
                    "bounded": 1,
                }

                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=8,
                )

                data = response.json()

                if not data:

                    continue

                nearest = None

                min_distance = float("inf")

                for place in data:

                    place_lat = float(place["lat"])

                    place_lng = float(place["lon"])

                    distance = calculate_distance(
                        lat,
                        lng,
                        place_lat,
                        place_lng,
                    )

                    if distance < min_distance:

                        min_distance = distance

                        nearest = place

                if nearest:

                    return {
                        "name": nearest.get("display_name", keyword),
                        "distance_km": round(min_distance, 2),
                    }

            except Exception:
                continue

        return None

    except Exception as e:

        print("Location error:", e)

        return None


# ==========================
# TEST
# ==========================
if __name__ == "__main__":

    vi_tri = get_current_location()

    print("Vi tri:", vi_tri)

    nearest = find_nearest_rest_stop()

    print("Gan nhat:", nearest)
