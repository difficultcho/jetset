from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, BigIntPK
from app.utils import utcnow


class Category(Base):
    """品类树：一级 parent_id=None，二级 parent_id 指向一级（仅支持两级）。

    商品挂在「叶子」上 —— 叶子 = 没有子类目的类目，与层级无关。
    一级类目如果没建二级，它自己就是叶子，商品可以直接挂上去；
    不是所有品类都需要细分，所以这是常规情况，不是脏数据。
    凡是「向上归并到一级类目」的派生逻辑，都要写成 parent_id or 自身 id。
    """

    __tablename__ = "category"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, default=None, index=True)
    name: Mapped[str] = mapped_column(String(64))
    en: Mapped[str] = mapped_column(String(64), default="", server_default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)


class Spu(Base):
    __tablename__ = "spu"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    # 叶子品类（无子类目者，一级二级皆可）
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), index=True)
    series_id: Mapped[int | None] = mapped_column(ForeignKey("series.id"), default=None, index=True)
    name: Mapped[str] = mapped_column(String(128))
    sub: Mapped[str] = mapped_column(String(128), default="", server_default="")  # 短名（卡片/走马灯）
    en_model: Mapped[str] = mapped_column(String(64), default="")  # 保留兼容
    code: Mapped[str] = mapped_column(String(64), default="", server_default="")   # 款号 AU433DSS266
    brief: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    bullets: Mapped[list | None] = mapped_column(JSON, default=None)  # 产品细节条目
    badge: Mapped[str | None] = mapped_column(String(16), default=None)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    has_video: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    # 展示价（分）= SKU 最低价，SKU 变更时同步维护，用于列表排序与展示
    price: Mapped[int] = mapped_column(Integer, default=0)
    original_price: Mapped[int | None] = mapped_column(Integer, default=None)  # 划线原价（折扣款）
    sales: Mapped[int] = mapped_column(Integer, default=0)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1 上架 0 下架
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    images: Mapped[list["SpuImage"]] = relationship(
        back_populates="spu", order_by="SpuImage.sort", lazy="selectin"
    )
    skus: Mapped[list["Sku"]] = relationship(back_populates="spu", lazy="selectin")


class SpuImage(Base):
    __tablename__ = "spu_image"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    spu_id: Mapped[int] = mapped_column(ForeignKey("spu.id"), index=True)
    color_index: Mapped[int] = mapped_column(Integer, default=0)
    url: Mapped[str] = mapped_column(String(512))
    sort: Mapped[int] = mapped_column(Integer, default=0)

    spu: Mapped[Spu] = relationship(back_populates="images")


class Sku(Base):
    __tablename__ = "sku"
    __table_args__ = (UniqueConstraint("spu_id", "color_index", "size"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    spu_id: Mapped[int] = mapped_column(ForeignKey("spu.id"), index=True)
    color_index: Mapped[int] = mapped_column(Integer, default=0)
    color_name: Mapped[str] = mapped_column(String(64), default="")
    color_hex: Mapped[str] = mapped_column(String(16), default="")
    size: Mapped[str] = mapped_column(String(16), default="均码")
    price: Mapped[int] = mapped_column(Integer)  # 单位：分
    stock: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)

    spu: Mapped[Spu] = relationship(back_populates="skus")
