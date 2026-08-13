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
    # 系列只有名字：商城右侧的图与文案由「商城配置」的 shop_menu 提供（支持多图+跳转）
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
