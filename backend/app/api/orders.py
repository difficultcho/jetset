from datetime import timedelta

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.deps import DB, CurrentUser
from app.errors import BizError
from app.models.order import Order, OrderStatus
from app.schemas.common import Page, Resp
from app.schemas.order import OrderCreateReq, OrderOut, PreviewOut, PreviewReq
from app.services import orders as svc
from app.services import wechat
from app.services.payment import get_provider
from app.utils import utcnow

router = APIRouter()


async def _get_owned(session, user_id: int, order_id: int) -> Order:
    order = (
        await session.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )
    ).scalar_one_or_none()
    if order is None or order.user_id != user_id:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order


@router.post("/orders/preview", response_model=Resp[PreviewOut])
async def preview(req: PreviewReq, user: CurrentUser, session: DB):
    return Resp(data=await svc.preview(session, user, req.items, req.user_coupon_id,
                                       req.use_points))


@router.post("/orders", response_model=Resp[OrderOut])
async def create_order(req: OrderCreateReq, user: CurrentUser, session: DB, request: Request):
    # 订单备注属 UGC，过内容安全检测
    if req.note and await wechat.msg_sec_check(user.openid, req.note) == "risky":
        raise BizError("备注包含违规内容，请修改")
    order = await svc.create_order(session, user, req.items, req.address_id, req.note,
                                   req.user_coupon_id, req.use_points)
    await session.commit()

    # 精确超时取消（best-effort；redis 不可用时由 worker 定时扫描兜底）
    arq_pool = getattr(request.app.state, "arq", None)
    if arq_pool is not None:
        try:
            await arq_pool.enqueue_job(
                "cancel_order_if_unpaid", order.id,
                _defer_by=timedelta(minutes=settings.order_timeout_minutes + 1),
            )
        except Exception:
            pass
    return Resp(data=svc.order_to_dict(await _get_owned(session, user.id, order.id)))


@router.get("/orders", response_model=Resp[Page[OrderOut]])
async def list_orders(
    user: CurrentUser,
    session: DB,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
):
    stmt = select(Order).where(Order.user_id == user.id)
    if status:
        if status not in OrderStatus.LABELS:
            raise BizError("无效的订单状态")
        stmt = stmt.where(Order.status == status)
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
        items=[svc.order_to_dict(o) for o in rows],
        total=total, page=page, page_size=page_size,
    ))


@router.get("/orders/{order_id}", response_model=Resp[OrderOut])
async def order_detail(order_id: int, user: CurrentUser, session: DB):
    return Resp(data=svc.order_to_dict(await _get_owned(session, user.id, order_id)))


@router.post("/orders/{order_id}/cancel", response_model=Resp[OrderOut])
async def cancel_order(order_id: int, user: CurrentUser, session: DB):
    order = await _get_owned(session, user.id, order_id)
    await svc.cancel_order(session, order)
    await session.commit()
    return Resp(data=svc.order_to_dict(order))


@router.post("/orders/{order_id}/confirm", response_model=Resp[OrderOut])
async def confirm_receipt(order_id: int, user: CurrentUser, session: DB):
    order = await _get_owned(session, user.id, order_id)
    await svc.confirm_receipt(session, order)
    await session.commit()
    return Resp(data=svc.order_to_dict(order))


@router.post("/orders/{order_id}/pay", response_model=Resp[dict])
async def pay_order(order_id: int, user: CurrentUser, session: DB):
    order = await _get_owned(session, user.id, order_id)
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise BizError("订单状态不可支付")
    if order.expire_at and order.expire_at < utcnow():
        raise BizError("订单已超时，请重新下单")
    return Resp(data=await get_provider().create_payment(order))
