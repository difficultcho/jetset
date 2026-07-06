from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK
from app.utils import utcnow


class PointsLog(Base):
    """积分流水。所有积分变动必须经 services/points 统一入口写入，
    保证 user.points 与流水一致、可审计。"""

    __tablename__ = "points_log"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    change: Mapped[int] = mapped_column(Integer)          # 正为获得，负为消耗
    balance_after: Mapped[int] = mapped_column(Integer)   # 变动后余额
    reason: Mapped[str] = mapped_column(String(32))       # order_reward/order_deduct/order_refund/admin_adjust
    ref_id: Mapped[int | None] = mapped_column(BigInteger, default=None)  # 关联订单等
    remark: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
