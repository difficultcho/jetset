from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.errors import BizError
from app.models.points import PointsLog
from app.models.user import User

REASON_LABELS = {
    "order_reward": "购物奖励",
    "order_deduct": "下单抵扣",
    "order_refund": "订单退回",
    "admin_adjust": "平台调整",
}


def deduct_cents(points: int) -> int:
    """积分 → 抵扣金额（分）。"""
    return points * 100 // settings.points_deduct_rate


def max_points_for(cents: int, balance: int) -> int:
    """给定剩余应付金额（分）与积分余额，可用的最大积分数。"""
    return min(balance, cents * settings.points_deduct_rate // 100)


async def _balance(session: AsyncSession, user_id: int) -> int:
    return (await session.execute(select(User.points).where(User.id == user_id))).scalar_one()


async def grant(session: AsyncSession, user_id: int, amount: int, reason: str,
                ref_id: int | None = None, remark: str = "") -> None:
    if amount <= 0:
        return
    await session.execute(
        update(User).where(User.id == user_id).values(points=User.points + amount)
    )
    session.add(PointsLog(
        user_id=user_id, change=amount, balance_after=await _balance(session, user_id),
        reason=reason, ref_id=ref_id, remark=remark,
    ))


async def deduct(session: AsyncSession, user_id: int, amount: int, reason: str,
                 ref_id: int | None = None, remark: str = "") -> None:
    if amount <= 0:
        return
    # 条件更新防并发扣负
    res = await session.execute(
        update(User)
        .where(User.id == user_id, User.points >= amount)
        .values(points=User.points - amount)
    )
    if res.rowcount == 0:
        raise BizError("积分不足")
    session.add(PointsLog(
        user_id=user_id, change=-amount, balance_after=await _balance(session, user_id),
        reason=reason, ref_id=ref_id, remark=remark,
    ))


async def list_logs(session: AsyncSession, user_id: int, limit: int = 100) -> list[PointsLog]:
    return (
        await session.execute(
            select(PointsLog).where(PointsLog.user_id == user_id)
            .order_by(PointsLog.id.desc()).limit(limit)
        )
    ).scalars().all()
