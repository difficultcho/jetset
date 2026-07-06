from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.deps import DB
from app.models.catalog import Spu
from app.models.order import Order, OrderStatus
from app.models.user import User
from app.models.wholesale import WholesaleApplication
from app.schemas.common import Resp
from app.utils import utcnow

router = APIRouter()


@router.get("/stats", response_model=Resp[dict])
async def stats(session: DB):
    since = utcnow() - timedelta(hours=24)

    async def count(stmt):
        return (await session.execute(stmt)).scalar_one()

    orders_24h = await count(select(func.count()).select_from(Order).where(Order.created_at >= since))
    gmv_24h = (
        await session.execute(
            select(func.coalesce(func.sum(Order.pay_amount), 0)).where(Order.paid_at >= since)
        )
    ).scalar_one()
    return Resp(data={
        "orders_24h": orders_24h,
        "gmv_24h": int(gmv_24h),  # 分
        "pending_shipment": await count(
            select(func.count()).select_from(Order).where(Order.status == OrderStatus.PENDING_SHIPMENT)
        ),
        "pending_wholesale": await count(
            select(func.count()).select_from(WholesaleApplication).where(WholesaleApplication.status == "pending")
        ),
        "users": await count(select(func.count()).select_from(User)),
        "products_on": await count(select(func.count()).select_from(Spu).where(Spu.status == 1)),
    })
