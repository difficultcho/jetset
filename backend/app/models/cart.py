from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK
from app.utils import utcnow


class CartItem(Base):
    __tablename__ = "cart_item"
    __table_args__ = (UniqueConstraint("user_id", "sku_id"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("sku.id"))
    qty: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
