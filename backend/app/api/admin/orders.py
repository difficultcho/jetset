from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.deps import DB
from app.errors import BizError
from app.models.order import Order, OrderStatus, Shipment
from app.schemas.admin import ShipReq
from app.schemas.common import Page, Resp
from app.services.orders import order_to_dict
from app.utils import utcnow

router = APIRouter()


def _admin_order(o: Order) -> dict:
    d = order_to_dict(o)
    d["user_id"] = o.user_id
    return d


@router.get("/orders", response_model=Resp[Page[dict]])
async def list_orders(
    session: DB,
    status: str | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(Order)
    if status:
        if status not in OrderStatus.LABELS:
            raise BizError("无效的订单状态")
        stmt = stmt.where(Order.status == status)
    if q:
        stmt = stmt.where(Order.order_no.like(f"%{q}%"))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await session.execute(
            stmt.options(selectinload(Order.items))
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return Resp(data=Page(
        items=[_admin_order(o) for o in rows],
        total=total, page=page, page_size=page_size,
    ))


@router.get("/orders/{order_id}", response_model=Resp[dict])
async def order_detail(order_id: int, session: DB):
    order = (
        await session.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    return Resp(data=_admin_order(order))


@router.post("/orders/{order_id}/ship", response_model=Resp[dict])
async def ship_order(order_id: int, req: ShipReq, session: DB):
    order = (
        await session.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status != OrderStatus.PENDING_SHIPMENT:
        raise BizError("当前状态不可发货")
    session.add(Shipment(order_id=order.id, company=req.company, tracking_no=req.tracking_no))
    order.status = OrderStatus.PENDING_RECEIPT
    order.shipped_at = utcnow()
    await session.commit()
    # TODO: 微信「发货信息录入」API + 订阅消息通知（上线前必接）
    return Resp(data={"id": order.id, "status": order.status})
