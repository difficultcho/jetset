"""arq 后台任务：
- cancel_order_if_unpaid: 下单时挂的精确延迟任务
- scan_expired_orders:    每 5 分钟兜底扫描（redis 挂掉期间创建的订单也能被取消）

运行: arq app.worker.WorkerSettings
"""

from arq.connections import RedisSettings
from arq.cron import cron
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db import SessionFactory
from app.models.order import Order, OrderStatus
from app.services.orders import cancel_expired_orders, cancel_order
from app.utils import utcnow


async def cancel_order_if_unpaid(ctx, order_id: int) -> str:
    async with SessionFactory() as session:
        order = (
            await session.execute(
                select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
            )
        ).scalar_one_or_none()
        if order is None or order.status != OrderStatus.PENDING_PAYMENT:
            return "skip"
        if order.expire_at and order.expire_at > utcnow():
            return "not-expired"
        await cancel_order(session, order)
        await session.commit()
        return "cancelled"


async def scan_expired_orders(ctx) -> int:
    async with SessionFactory() as session:
        count = await cancel_expired_orders(session)
        await session.commit()
        return count


class WorkerSettings:
    functions = [cancel_order_if_unpaid]
    # 每 5 分钟兜底扫描一次
    cron_jobs = [cron(scan_expired_orders, minute=set(range(0, 60, 5)))]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
