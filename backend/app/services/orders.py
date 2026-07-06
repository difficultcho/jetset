from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.errors import BizError
from app.models.address import Address
from app.models.catalog import Sku, Spu
from app.models.order import Order, OrderItem, OrderStatus, Payment
from app.models.user import User
from app.schemas.order import OrderLineReq
from app.utils import gen_order_no, utcnow


def _merge_lines(items: list[OrderLineReq]) -> dict[int, int]:
    """同 SKU 合并数量。"""
    merged: dict[int, int] = {}
    for it in items:
        merged[it.sku_id] = merged.get(it.sku_id, 0) + it.qty
    return merged


async def _load_skus(session: AsyncSession, sku_ids: list[int]) -> dict[int, Sku]:
    rows = (
        await session.execute(
            select(Sku).options(selectinload(Sku.spu)).where(Sku.id.in_(sku_ids))
        )
    ).scalars().all()
    sku_map = {s.id: s for s in rows}
    for sid in sku_ids:
        sku = sku_map.get(sid)
        if sku is None or sku.status != 1 or sku.spu.status != 1:
            raise BizError("部分商品已下架，请刷新后重试")
    return sku_map


def _color_image(sku: Sku) -> str:
    for img in sku.spu.images:
        if img.color_index == sku.color_index:
            return img.url
    return sku.spu.images[0].url if sku.spu.images else ""


def _build_line(sku: Sku, qty: int) -> dict:
    return {
        "sku_id": sku.id,
        "spu_id": sku.spu_id,
        "name": sku.spu.name,
        "en_model": sku.spu.en_model,
        "color_name": sku.color_name,
        "color_hex": sku.color_hex,
        "size": sku.size,
        "image": _color_image(sku),
        "price": sku.price,
        "qty": qty,
    }


def _amounts(lines: list[dict]) -> dict:
    item_amount = sum(line["price"] * line["qty"] for line in lines)
    freight = settings.freight_cents
    discount = 0  # 二期：优惠券/促销在此收口
    return {
        "item_amount": item_amount,
        "freight": freight,
        "discount_amount": discount,
        "pay_amount": item_amount + freight - discount,
    }


async def preview(session: AsyncSession, items: list[OrderLineReq]) -> dict:
    merged = _merge_lines(items)
    sku_map = await _load_skus(session, list(merged))
    lines = [_build_line(sku_map[sid], qty) for sid, qty in merged.items()]
    return {"items": lines, "coupons": [], **_amounts(lines)}


async def create_order(session: AsyncSession, user: User, items: list[OrderLineReq],
                       address_id: int, note: str) -> Order:
    address = await session.get(Address, address_id)
    if address is None or address.user_id != user.id:
        raise BizError("请选择有效的收货地址")

    merged = _merge_lines(items)
    sku_map = await _load_skus(session, list(merged))

    # 条件更新扣库存（stock >= qty 才生效），防超卖；任一失败整单回滚
    for sid, qty in merged.items():
        res = await session.execute(
            update(Sku)
            .where(Sku.id == sid, Sku.stock >= qty)
            .values(stock=Sku.stock - qty)
        )
        if res.rowcount == 0:
            raise BizError(f"「{sku_map[sid].spu.name}」库存不足")

    lines = [_build_line(sku_map[sid], qty) for sid, qty in merged.items()]
    am = _amounts(lines)
    order = Order(
        order_no=gen_order_no(),
        user_id=user.id,
        status=OrderStatus.PENDING_PAYMENT,
        note=note,
        address_snapshot={
            "name": address.name,
            "phone": address.phone,
            "region": address.region,
            "detail": address.detail,
        },
        expire_at=utcnow() + timedelta(minutes=settings.order_timeout_minutes),
        **am,
    )
    session.add(order)
    await session.flush()
    for line in lines:
        session.add(OrderItem(order_id=order.id, **line))
    return order


async def cancel_order(session: AsyncSession, order: Order) -> None:
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise BizError("当前状态不可取消")
    order.status = OrderStatus.CANCELLED
    order.cancelled_at = utcnow()
    for item in order.items:  # 回补库存
        await session.execute(
            update(Sku).where(Sku.id == item.sku_id).values(stock=Sku.stock + item.qty)
        )


async def mark_order_paid(session: AsyncSession, order: Order,
                          provider: str, external_id: str | None = None) -> bool:
    """支付回调入口，必须幂等：已处理过直接返回 False。"""
    if order.status != OrderStatus.PENDING_PAYMENT:
        return False
    order.status = OrderStatus.PENDING_SHIPMENT
    order.paid_at = utcnow()
    session.add(Payment(
        order_id=order.id, provider=provider, external_id=external_id,
        amount=order.pay_amount, status="paid", paid_at=order.paid_at,
    ))
    for item in order.items:  # 累计销量
        await session.execute(
            update(Spu).where(Spu.id == item.spu_id).values(sales=Spu.sales + item.qty)
        )
    return True


async def confirm_receipt(session: AsyncSession, order: Order) -> None:
    if order.status != OrderStatus.PENDING_RECEIPT:
        raise BizError("当前状态不可确认收货")
    order.status = OrderStatus.PENDING_REVIEW
    order.completed_at = utcnow()


async def cancel_expired_orders(session: AsyncSession) -> int:
    """兜底扫描：超时未支付的订单批量取消（worker 定时调用）。"""
    rows = (
        await session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.status == OrderStatus.PENDING_PAYMENT, Order.expire_at < utcnow())
        )
    ).scalars().all()
    for order in rows:
        await cancel_order(session, order)
    return len(rows)


def order_to_dict(order: Order) -> dict:
    return {
        "id": order.id,
        "order_no": order.order_no,
        "status": order.status,
        "status_label": OrderStatus.LABELS.get(order.status, order.status),
        "item_amount": order.item_amount,
        "discount_amount": order.discount_amount,
        "freight": order.freight,
        "pay_amount": order.pay_amount,
        "note": order.note,
        "address": order.address_snapshot,
        "items": [
            {
                "sku_id": i.sku_id, "spu_id": i.spu_id, "name": i.name,
                "en_model": i.en_model, "color_name": i.color_name,
                "color_hex": i.color_hex, "size": i.size, "image": i.image,
                "price": i.price, "qty": i.qty,
            }
            for i in order.items
        ],
        "shipment": (
            {"company": order.shipment.company, "tracking_no": order.shipment.tracking_no,
             "shipped_at": order.shipped_at}
            if order.shipment else None
        ),
        "expire_at": order.expire_at,
        "paid_at": order.paid_at,
        "created_at": order.created_at,
    }
