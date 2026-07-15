from datetime import timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import BizError
from app.models.coupon import Coupon, UserCoupon
from app.models.user import User
from app.utils import utcnow


def uc_status(uc: UserCoupon) -> str:
    """惰性判定：unused 且已过期 → expired"""
    if uc.status == "unused" and uc.expires_at < utcnow():
        return "expired"
    return uc.status


def uc_to_dict(uc: UserCoupon, item_amount: int | None = None) -> dict:
    d = {
        "id": uc.id,
        "name": uc.name,
        "threshold": uc.threshold,
        "amount": uc.amount,
        "status": uc_status(uc),
        "expires_at": uc.expires_at,
    }
    if item_amount is not None:
        d["usable"] = uc_status(uc) == "unused" and uc.threshold <= item_amount
    return d


def _expires_at(coupon: Coupon):
    cands = []
    if coupon.valid_days:
        cands.append(utcnow() + timedelta(days=coupon.valid_days))
    if coupon.valid_until:
        cands.append(coupon.valid_until)
    return min(cands) if cands else utcnow() + timedelta(days=365)


async def _issue(session: AsyncSession, user: User, coupon: Coupon) -> UserCoupon:
    """发放一张券给用户（限领校验 + 条件更新占名额防超发）。"""
    claimed = (
        await session.execute(
            select(func.count()).select_from(UserCoupon).where(
                UserCoupon.user_id == user.id, UserCoupon.coupon_id == coupon.id
            )
        )
    ).scalar_one()
    if claimed >= coupon.per_user_limit:
        raise BizError("已达每人限领数量")

    res = await session.execute(
        update(Coupon)
        .where(
            Coupon.id == coupon.id,
            Coupon.status == 1,
            or_(Coupon.total == 0, Coupon.taken < Coupon.total),
        )
        .values(taken=Coupon.taken + 1)
    )
    if res.rowcount == 0:
        raise BizError("手慢了，已被领完")

    uc = UserCoupon(
        user_id=user.id, coupon_id=coupon.id, name=coupon.name,
        threshold=coupon.threshold, amount=coupon.amount,
        expires_at=_expires_at(coupon),
    )
    session.add(uc)
    await session.flush()
    return uc


async def claim(session: AsyncSession, user: User, coupon_id: int) -> UserCoupon:
    """领券中心手动领取。"""
    coupon = await session.get(Coupon, coupon_id)
    if coupon is None or coupon.status != 1:
        raise BizError("优惠券不存在或已下架")
    if coupon.is_newcomer:
        raise BizError("新人专享券，注册时自动发放")
    if coupon.valid_until and coupon.valid_until < utcnow():
        raise BizError("该券活动已结束")
    return await _issue(session, user, coupon)


async def grant_newcomer_coupons(session: AsyncSession, user: User) -> list[UserCoupon]:
    """注册时自动发放全部在架新客券；单张失败（领完等）静默跳过，不阻塞注册。"""
    rows = (
        await session.execute(
            select(Coupon).where(
                Coupon.is_newcomer.is_(True),
                Coupon.status == 1,
                or_(Coupon.valid_until.is_(None), Coupon.valid_until >= utcnow()),
            )
        )
    ).scalars().all()
    granted = []
    for coupon in rows:
        try:
            granted.append(await _issue(session, user, coupon))
        except BizError:
            continue
    return granted


async def list_my_coupons(session: AsyncSession, user_id: int) -> list[UserCoupon]:
    return (
        await session.execute(
            select(UserCoupon)
            .where(UserCoupon.user_id == user_id)
            .order_by(UserCoupon.id.desc())
        )
    ).scalars().all()


async def usable_coupons(session: AsyncSession, user_id: int) -> list[UserCoupon]:
    """未使用且未过期的券（门槛是否满足由调用方按订单金额判断）。"""
    return (
        await session.execute(
            select(UserCoupon).where(
                UserCoupon.user_id == user_id,
                UserCoupon.status == "unused",
                UserCoupon.expires_at >= utcnow(),
            ).order_by(UserCoupon.amount.desc(), UserCoupon.expires_at.asc())
        )
    ).scalars().all()


async def get_valid_for_order(session: AsyncSession, user_id: int,
                              uc_id: int, item_amount: int) -> UserCoupon:
    """校验券可用于该订单金额（不锁定）。"""
    uc = await session.get(UserCoupon, uc_id)
    if uc is None or uc.user_id != user_id:
        raise BizError("优惠券不存在")
    if uc_status(uc) != "unused":
        raise BizError("优惠券不可用")
    if uc.threshold > item_amount:
        raise BizError("未满足优惠券使用门槛")
    return uc


async def lock_for_order(session: AsyncSession, uc: UserCoupon, order_id: int) -> None:
    """把券锁定到订单上（条件更新防并发重复使用），失败整单回滚。"""
    res = await session.execute(
        update(UserCoupon)
        .where(UserCoupon.id == uc.id, UserCoupon.status == "unused")
        .values(status="used", used_order_id=order_id, used_at=utcnow())
    )
    if res.rowcount == 0:
        raise BizError("优惠券已被使用")


async def release_for_order(session: AsyncSession, order_id: int) -> None:
    """订单取消/超时后退券（过期与否由展示层惰性判定）。"""
    await session.execute(
        update(UserCoupon)
        .where(UserCoupon.used_order_id == order_id, UserCoupon.status == "used")
        .values(status="unused", used_order_id=None, used_at=None)
    )
