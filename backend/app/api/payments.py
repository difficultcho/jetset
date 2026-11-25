import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.deps import DB
from app.errors import BizError
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.schemas.common import Resp
from app.services.orders import mark_order_paid
from app.services.wxpay import NotifyError, client_from_settings, parse_notify

logger = logging.getLogger(__name__)

router = APIRouter()


class MockConfirmReq(BaseModel):
    order_no: str


async def _mock_confirm(req: MockConfirmReq, session: DB):
    """模拟支付成功回调（仅 MOCK_MODE=true 时挂载）。"""
    order = (
        await session.execute(
            select(Order).options(selectinload(Order.items)).where(Order.order_no == req.order_no)
        )
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="订单不存在")
    changed = await mark_order_paid(session, order, provider="mock")
    await session.commit()
    return Resp(data={"order_no": order.order_no, "status": order.status, "changed": changed})


# 假支付端点只在 mock 模式下注册：关掉后这条路由根本不存在，也不出现在 /docs 里。
# 比"注册了但运行期返回 404"更彻底——提审时不会有个能白拿订单的端点在线。
if settings.mock_mode:
    router.post("/payments/mock/confirm", response_model=Resp[dict])(_mock_confirm)


def _fail(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": "FAIL", "message": message})


async def _apply_notify(session, raw: bytes, headers) -> None:
    try:
        wx = client_from_settings()
    except BizError:
        raise NotifyError(503, "微信支付未配置") from None
    txn = parse_notify(
        raw, headers,
        public_key=wx.public_key, public_key_id=wx.public_key_id, apiv3_key=wx.apiv3_key,
    )
    if txn.get("trade_state") != "SUCCESS":
        return

    out_trade_no = txn.get("out_trade_no")
    if not isinstance(out_trade_no, str) or not out_trade_no:
        raise NotifyError(400, "订单不存在")
    order = (
        await session.execute(
            select(Order).options(selectinload(Order.items)).where(Order.order_no == out_trade_no)
        )
    ).scalar_one_or_none()
    if order is None:
        raise NotifyError(404, "订单不存在")
    if order.status == OrderStatus.CANCELLED:
        logger.warning("wxpay success for cancelled order %s", order.order_no)
        raise NotifyError(500, "订单已关闭")
    if order.status != OrderStatus.PENDING_PAYMENT:
        return

    if txn.get("mchid") != settings.wxpay_mchid.strip() or txn.get("appid") != settings.wechat_appid.strip():
        raise NotifyError(400, "商户信息不匹配")
    amount = txn.get("amount")
    if (not isinstance(amount, dict) or amount.get("total") != order.pay_amount
            or amount.get("currency") != "CNY"):
        raise NotifyError(400, "金额不匹配")
    payer = txn.get("payer")
    openid = payer.get("openid") if isinstance(payer, dict) else None
    user = await session.get(User, order.user_id)
    if user is None or not isinstance(openid, str) or openid != user.openid:
        raise NotifyError(400, "付款人不匹配")
    external_id = txn.get("transaction_id")
    if not isinstance(external_id, str) or not external_id or len(external_id) > 64:
        raise NotifyError(400, "缺少交易号")
    await mark_order_paid(session, order, provider="wechat", external_id=external_id)


@router.post("/payments/wechat/notify")
async def wechat_notify(request: Request, session: DB):
    """微信支付结果通知。没有用户登录态。成功必须是 HTTP 200 的 SUCCESS，不能走业务信封。"""
    raw = await request.body()
    try:
        await _apply_notify(session, raw, request.headers)
        await session.commit()
    except NotifyError as exc:
        await session.rollback()
        return _fail(exc.http_status, exc.message)
    except Exception:
        logger.exception("wxpay notify failed")
        await session.rollback()
        return _fail(500, "处理失败")
    return JSONResponse(status_code=200, content={"code": "SUCCESS", "message": "成功"})
