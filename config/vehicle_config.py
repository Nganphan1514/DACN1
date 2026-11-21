import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# CAU HINH XE
VEHICLE_ID = int(os.getenv("VEHICLE_ID", "1"))
VEHICLE_NAME = os.getenv("VEHICLE_NAME", "43A-123.45")
