import requests


def get_nearby_rest_stop():

    # GPS giả lập
    lat = 16.0544
    lon = 108.2022

    overpass_url = "https://overpass-api.de/api/interpreter"

    query = f"""
    [out:json];
    (
      node
      ["amenity"="fuel"]
      (around:5000,{lat},{lon});
    );
    out;
    """

    response = requests.get(overpass_url, params={"data": query})

    data = response.json()

    if len(data["elements"]) > 0:

        place = data["elements"][0]

        return "trạm dừng nghỉ gần nhất"

    return None
