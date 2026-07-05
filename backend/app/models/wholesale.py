from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK
from app.utils import utcnow


class WholesaleApplication(Base):
    __tablename__ = "wholesale_application"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    type: Mapped[str] = mapped_column(String(32))  # 经销商/分销商/门店合作/其他
    phone: Mapped[str] = mapped_column(String(20))
    company: Mapped[str] = mapped_column(String(128))
    region: Mapped[str] = mapped_column(String(128), default="")
    license_img: Mapped[str] = mapped_column(String(512))
    store_img: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/approved/rejected
    review_note: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
