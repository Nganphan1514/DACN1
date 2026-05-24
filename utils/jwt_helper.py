import jwt

from datetime import datetime, timedelta

from config.app_config import JWT_SECRET_KEY


def create_token(user):

    payload = {
        "id": user["id"],
        "username": user["ten_dang_nhap"],
        "role": user["vai_tro"],
        "exp": datetime.utcnow() + timedelta(days=1),
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

    return token


def decode_token(token):

    try:

        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])

        return payload

    except:

        return None
