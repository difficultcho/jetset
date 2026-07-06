import hashlib
import hmac
import os
from datetime import timedelta

import jwt

from app.config import settings
from app.utils import utcnow

ALGO = "HS256"


def create_token(subject_id: int, admin: bool = False) -> str:
    payload = {
        "sub": str(subject_id),
        "adm": admin,
        "exp": utcnow() + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def parse_token(token: str) -> tuple[int, bool] | None:
    """返回 (subject_id, is_admin)；无效返回 None。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
        return int(payload["sub"]), bool(payload.get("adm", False))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


# 管理员密码：pbkdf2-sha256，标准库实现避免额外依赖
def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + dk.hex()


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split(":")
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 100_000)
    return hmac.compare_digest(dk.hex(), dk_hex)
