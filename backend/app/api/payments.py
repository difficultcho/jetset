from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.deps import DB
from app.models.order import Order
from app.schemas.common import Resp
from app.services.orders import mark_order_paid

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


@router.post("/payments/wechat/notify")
async def wechat_notify():
    """微信支付回调（待商户号配置后实现：验签 → 解密 → mark_order_paid）。"""
    raise HTTPException(status_code=501, detail="微信支付回调尚未实现")
