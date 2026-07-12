from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK
from app.utils import utcnow


class Store(Base):
    """线下门店。距离由前端用用户定位 + lat/lng 实时计算，不入库。"""

    __tablename__ = "store"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))          # 北京三里屯精品店
    short_name: Mapped[str] = mapped_column(String(64), default="")  # 北京三里屯
    province: Mapped[str] = mapped_column(String(32), default="", index=True)
    city: Mapped[str] = mapped_column(String(32), default="", index=True)
    address: Mapped[str] = mapped_column(String(256), default="")
    tel: Mapped[str] = mapped_column(String(32), default="")
    business_hours: Mapped[str] = mapped_column(String(128), default="")
    images: Mapped[list] = mapped_column(JSON, default=list)   # 门店图/门头/内景
    consultant_qr: Mapped[str] = mapped_column(String(512), default="")  # 导购二维码
    lat: Mapped[float | None] = mapped_column(Float, default=None)
    lng: Mapped[float | None] = mapped_column(Float, default=None)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
