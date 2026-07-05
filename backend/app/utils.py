import random
from datetime import datetime, timezone


def utcnow() -> datetime:
    """统一使用无时区 UTC 时间（DB 列均为 naive UTC）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def gen_order_no() -> str:
    """订单号：时间戳 + 4 位随机数，如 20260705213045 + 8271。"""
    return utcnow().strftime("%Y%m%d%H%M%S") + f"{random.randint(0, 9999):04d}"
