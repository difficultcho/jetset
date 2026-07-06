from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK
from app.utils import utcnow


class Coupon(Base):
    """券模板（MVP 仅满减券，全场通用）。"""

    __tablename__ = "coupon"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    threshold: Mapped[int] = mapped_column(Integer, default=0)  # 门槛（分），0=无门槛
    amount: Mapped[int] = mapped_column(Integer)                # 减免（分）
    total: Mapped[int] = mapped_column(Integer, default=0)      # 发行量，0=不限
    taken: Mapped[int] = mapped_column(Integer, default=0)
    per_user_limit: Mapped[int] = mapped_column(Integer, default=1)
    valid_days: Mapped[int | None] = mapped_column(Integer, default=None)      # 领取后 N 天有效
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, default=None)  # 固定截止
    status: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1 可领取 0 下架
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserCoupon(Base):
    """用户持有的券。name/threshold/amount 为领取时快照，模板改动不影响已领券。

    status 只存 unused/used；「已过期」由 unused + expires_at < now 惰性判定。
    """

    __tablename__ = "user_coupon"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupon.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    threshold: Mapped[int] = mapped_column(Integer, default=0)
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="unused")  # unused | used
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_order_id: Mapped[int | None] = mapped_column(BigInteger, default=None, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    claimed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
