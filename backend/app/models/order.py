from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, BigIntPK
from app.utils import utcnow


class OrderStatus:
    PENDING_PAYMENT = "pending_payment"
    PENDING_SHIPMENT = "pending_shipment"
    PENDING_RECEIPT = "pending_receipt"
    PENDING_REVIEW = "pending_review"  # 已停用。旧单由定时任务收成已完成。
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUND_PENDING = "refund_pending"  # 已提交退款，钱还没到账
    REFUNDED = "refunded"

    LABELS = {
        PENDING_PAYMENT: "待付款",
        PENDING_SHIPMENT: "待发货",
        PENDING_RECEIPT: "待收货",
        PENDING_REVIEW: "待评价",
        COMPLETED: "已完成",
        CANCELLED: "已取消",
        REFUND_PENDING: "退款中",
        REFUNDED: "已退款",
    }


class Order(Base):
    __tablename__ = "orders"  # order 是 SQL 保留字

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=OrderStatus.PENDING_PAYMENT, index=True)
    item_amount: Mapped[int] = mapped_column(Integer, default=0)  # 分
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)  # 优惠券折扣
    points_used: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # 抵扣消耗的积分数
    freight: Mapped[int] = mapped_column(Integer, default=0)
    pay_amount: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    address_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", lazy="selectin")
    shipment: Mapped["Shipment | None"] = relationship(lazy="selectin")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="order", lazy="selectin")


class OrderItem(Base):
    __tablename__ = "order_item"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    sku_id: Mapped[int] = mapped_column(BigInteger)
    spu_id: Mapped[int] = mapped_column(BigInteger)
    # 下单时快照，商品后续改动不影响历史订单
    name: Mapped[str] = mapped_column(String(128))
    en_model: Mapped[str] = mapped_column(String(64), default="")
    color_name: Mapped[str] = mapped_column(String(64), default="")
    color_hex: Mapped[str] = mapped_column(String(16), default="")
    size: Mapped[str] = mapped_column(String(16), default="")
    image: Mapped[str] = mapped_column(String(512), default="")
    price: Mapped[int] = mapped_column(Integer)  # 成交单价（分）
    qty: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="items")


class Shipment(Base):
    __tablename__ = "shipment"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    company: Mapped[str] = mapped_column(String(32))
    tracking_no: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Payment(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    provider: Mapped[str] = mapped_column(String(16))  # mock | wechat
    external_id: Mapped[str | None] = mapped_column(String(64), default=None)  # 微信 transaction_id
    amount: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="paid")  # created | paid | refunded
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Refund(Base):
    """整单退款。客服核验后由管理后台发起。失败时用同一退款单号重试。"""

    __tablename__ = "refund"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    out_refund_no: Mapped[str] = mapped_column(String(64), unique=True)
    reason: Mapped[str] = mapped_column(String(80), default="")
    reject_reason: Mapped[str] = mapped_column(String(80), default="")
    # pending 待提交 | processing 微信处理中 | success | rejected 旧数据 | failed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    previous_status: Mapped[str] = mapped_column(String(32))  # 拒绝时退回这个订单状态
    amount: Mapped[int] = mapped_column(Integer)  # 分，整单实付
    wechat_refund_id: Mapped[str | None] = mapped_column(String(64), default=None)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    order: Mapped[Order] = relationship(back_populates="refunds")
