from datetime import timedelta

import jwt

from app.config import settings
from app.utils import utcnow

ALGO = "HS256"


def create_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": utcnow() + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def parse_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
