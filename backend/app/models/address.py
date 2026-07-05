from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK
from app.utils import utcnow


class Address(Base):
    __tablename__ = "address"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str] = mapped_column(String(20))
    region: Mapped[str] = mapped_column(String(128), default="")  # 省 市 区
    detail: Mapped[str] = mapped_column(String(256))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
