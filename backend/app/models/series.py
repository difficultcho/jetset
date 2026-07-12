from datetime import datetime

from sqlalchemy import DateTime, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK
from app.utils import utcnow


class Series(Base):
    """系列（策展合集）：跨品类聚合商品，如 HIGH SUMMER 2026 夏日胶囊系列。
    与 category（品类树）正交——商品属于一个二级品类，可归入一个系列（1:N）。"""

    __tablename__ = "series"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))            # 2026夏日胶囊系列
    en: Mapped[str] = mapped_column(String(64), default="")  # HIGH SUMMER
    subtitle: Mapped[str] = mapped_column(String(128), default="")
    cover_tint: Mapped[str] = mapped_column(String(16), default="#e8dcc8")  # 大卡占位色
    cover: Mapped[str] = mapped_column(String(512), default="")             # 真实封面图
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
