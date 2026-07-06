from datetime import datetime

from pydantic import BaseModel, Field


class OrderLineReq(BaseModel):
    sku_id: int
    qty: int = Field(ge=1, le=999)


class PreviewReq(BaseModel):
    items: list[OrderLineReq] = Field(min_length=1)
    user_coupon_id: int | None = None


class OrderCreateReq(BaseModel):
    items: list[OrderLineReq] = Field(min_length=1)
    address_id: int
    note: str = Field(default="", max_length=250)
    user_coupon_id: int | None = None


class OrderItemOut(BaseModel):
    sku_id: int
    spu_id: int
    name: str
    en_model: str
    color_name: str
    color_hex: str
    size: str
    image: str
    price: int
    qty: int


class PreviewOut(BaseModel):
    items: list[OrderItemOut]
    item_amount: int
    discount_amount: int
    freight: int
    pay_amount: int
    coupons: list[dict] = []       # 用户可用券（含 usable 门槛标记）
    applied_coupon_id: int | None = None


class OrderOut(BaseModel):
    id: int
    order_no: str
    status: str
    status_label: str
    item_amount: int
    discount_amount: int
    freight: int
    pay_amount: int
    note: str
    address: dict
    items: list[OrderItemOut]
    shipment: dict | None = None  # {company, tracking_no, shipped_at}
    expire_at: datetime | None
    paid_at: datetime | None
    created_at: datetime
