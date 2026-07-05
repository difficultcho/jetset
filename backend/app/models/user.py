from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK
from app.utils import utcnow


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    unionid: Mapped[str | None] = mapped_column(String(64), default=None)
    phone: Mapped[str | None] = mapped_column(String(20), default=None)
    name: Mapped[str] = mapped_column(String(64), default="")
    avatar: Mapped[str] = mapped_column(String(512), default="")
    gender: Mapped[str] = mapped_column(String(4), default="")
    birthday: Mapped[str] = mapped_column(String(16), default="")
    region: Mapped[str] = mapped_column(String(128), default="")
    reco_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1 正常 0 禁用
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
