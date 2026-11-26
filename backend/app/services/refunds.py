"""整单退款。

顾客不能在小程序里申请。管理端在客服核验后直接退：mock 立即完成，正式环境调微信退款。
未发货的已支付订单、待收货和已完成都可以退，代码不锁 7 天。失败用同一退款单号重试。
成功后回补库存、回退销量、退券、退还抵扣积分，并按余额扣回购物奖励。
发货管理里显示已退款，还要该单已经录入过发货信息。经营税不在这里处理。
"""

import re

from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.errors import BizError
from app.models.catalog import Sku, Spu
from app.models.order import Order, OrderStatus, Payment, Refund
from app.services import coupons as coupon_svc
from app.services import points as points_svc
from app.services.wxpay import NotifyError, client_from_settings
from app.utils import utcnow

_REFUND_NO = re.compile(r"[0-9A-Za-z_\-|*]{6,64}")
_ADMIN_OK = {
    OrderStatus.PENDING_SHIPMENT,
    OrderStatus.PENDING_RECEIPT,
    OrderStatus.COMPLETED,
}
REFUND_LABELS = {
    "pending": "待提交",
    "processing": "退款处理中",
    "success": "已退款",
    "rejected": "已拒绝",
    "failed": "退款异常",
}


def _latest(order: Order) -> Refund | None:
    rows = [row for row in order.refunds if row.id is not None]
    if not rows:
        pending = [row for row in order.refunds if row.status == "pending"]
        return pending[-1] if pending else None
    return max(rows, key=lambda row: row.id)


def refund_fields(order: Order) -> dict:
    row = _latest(order)
    refund = None
    if row is not None:
        refund = {
            "status": row.status,
            "status_label": REFUND_LABELS.get(row.status, row.status),
            "reason": row.reason,
            "reject_reason": row.reject_reason or "",
            "created_at": row.created_at,
            "refunded_at": row.refunded_at,
        }
    return {"can_refund": False, "refund": refund}


def _next_no(order: Order) -> str:
    used = {row.out_refund_no for row in order.refunds}
    base = "R" + order.order_no
    if base not in used and _REFUND_NO.fullmatch(base):
        return base
    n = 2
    while n < 100:
        candidate = f"{base}{n}"
        if candidate not in used and _REFUND_NO.fullmatch(candidate):
            return candidate
        n += 1
    raise BizError("无法生成退款单号")


def _retry_row(order: Order) -> Refund | None:
    row = _latest(order)
    if row is None or row.status == "rejected":
        return None
    if row.status == "success" or order.status == OrderStatus.REFUNDED:
        raise BizError("当前状态不可退款")
    if row.status == "processing":
        raise BizError("退款处理中")
    if row.status in ("failed", "pending") and order.status == OrderStatus.REFUND_PENDING:
        return row
    if row.status in ("failed", "pending"):
        raise BizError("当前状态不可退款")
    return None


async def _submit(session: AsyncSession, order: Order, refund: Refund) -> None:
    refund.decided_at = utcnow()
    if settings.mock_mode:
        await finalize_refund(session, order, refund)
        return
    result = await client_from_settings().create_refund(
        out_trade_no=order.order_no,
        out_refund_no=refund.out_refund_no,
        amount=order.pay_amount,
        reason=refund.reason,
    )
    if result["refund_id"]:
        refund.wechat_refund_id = result["refund_id"]
    status = result["status"]
    if status == "SUCCESS":
        await finalize_refund(session, order, refund)
    elif status == "PROCESSING":
        refund.status = "processing"
    elif status in ("CLOSED", "ABNORMAL"):
        refund.status = "failed"
    else:
        raise BizError("微信退款失败，请稍后重试", http_status=502)


async def admin_refund(session: AsyncSession, order: Order, reason: str) -> None:
    """客服核验后整单原路退。失败的单用原来的 out_refund_no 再提交。"""
    refund = _retry_row(order)
    text = (reason or "").strip()[:80]
    if refund is None:
        if order.status not in _ADMIN_OK:
            raise BizError("当前状态不可退款")
        refund = Refund(
            order_id=order.id,
            out_refund_no=_next_no(order),
            reason=text or "客服确认退款",
            status="pending",
            previous_status=order.status,
            amount=order.pay_amount,
        )
        order.refunds.append(refund)
        session.add(refund)
        order.status = OrderStatus.REFUND_PENDING
        await session.flush()
    elif text:
        refund.reason = text
    await _submit(session, order, refund)


async def finalize_refund(session: AsyncSession, order: Order, refund: Refund) -> bool:
    """退款成功只做一次。已经退过的直接返回。"""
    if order.status == OrderStatus.REFUNDED:
        if refund.status != "success":
            refund.status = "success"
            if refund.refunded_at is None:
                refund.refunded_at = utcnow()
        return False
    now = utcnow()
    res = await session.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == OrderStatus.REFUND_PENDING)
        .values(status=OrderStatus.REFUNDED)
    )
    if res.rowcount == 0:
        return False
    order.status = OrderStatus.REFUNDED
    for item in order.items:
        await session.execute(
            update(Sku).where(Sku.id == item.sku_id).values(stock=Sku.stock + item.qty)
        )
        await session.execute(
            update(Spu).where(Spu.id == item.spu_id).values(
                sales=case((Spu.sales >= item.qty, Spu.sales - item.qty), else_=0)
            )
        )
    await coupon_svc.release_for_order(session, order.id)
    reward = order.pay_amount // 100 * settings.points_per_yuan
    if reward > 0:
        await points_svc.revoke_up_to(
            session, order.user_id, reward, "order_reward_revoke",
            ref_id=order.id, remark=order.order_no,
        )
    if order.points_used > 0:
        await points_svc.grant(
            session, order.user_id, order.points_used, "order_refund",
            ref_id=order.id, remark=order.order_no,
        )
    await session.execute(
        update(Payment)
        .where(Payment.order_id == order.id, Payment.status == "paid")
        .values(status="refunded")
    )
    refund.status = "success"
    refund.refunded_at = now
    return True


async def handle_notify(session: AsyncSession, data: dict) -> None:
    out_refund_no = data.get("out_refund_no")
    if not isinstance(out_refund_no, str) or not out_refund_no:
        raise NotifyError(400, "退款单不存在")
    refund = (
        await session.execute(select(Refund).where(Refund.out_refund_no == out_refund_no))
    ).scalar_one_or_none()
    if refund is None:
        raise NotifyError(404, "退款单不存在")
    order = (
        await session.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.refunds))
            .where(Order.id == refund.order_id)
        )
    ).scalar_one()
    if data.get("mchid") != settings.wxpay_mchid.strip():
        raise NotifyError(400, "商户信息不匹配")
    if data.get("out_trade_no") != order.order_no:
        raise NotifyError(400, "订单不匹配")
    amount = data.get("amount")
    if (not isinstance(amount, dict) or amount.get("refund") != order.pay_amount
            or amount.get("total") != order.pay_amount
            or amount.get("currency") not in (None, "CNY")):
        raise NotifyError(400, "金额不匹配")
    refund_id = data.get("refund_id")
    if isinstance(refund_id, str) and refund_id and len(refund_id) <= 64:
        refund.wechat_refund_id = refund_id
    status = data.get("refund_status")
    if status == "SUCCESS":
        if refund.status == "rejected":
            raise NotifyError(500, "退款单已拒绝")
        await finalize_refund(session, order, refund)
        return
    if status in ("CLOSED", "ABNORMAL"):
        if order.status == OrderStatus.REFUNDED or refund.status in ("success", "rejected"):
            return
        refund.status = "failed"
        return
    raise NotifyError(500, "退款状态无法处理")
