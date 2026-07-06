from fastapi import APIRouter
from sqlalchemy import func, or_, select

from app.deps import DB, CurrentUser
from app.models.coupon import Coupon, UserCoupon
from app.schemas.common import Resp
from app.services import coupons as svc
from app.utils import utcnow

router = APIRouter()


@router.get("/coupons/center", response_model=Resp[list[dict]])
async def center(user: CurrentUser, session: DB):
    """领券中心：可领取的券 + 本人领取状态。"""
    rows = (
        await session.execute(
            select(Coupon)
            .where(
                Coupon.status == 1,
                or_(Coupon.valid_until.is_(None), Coupon.valid_until >= utcnow()),
            )
            .order_by(Coupon.id.desc())
        )
    ).scalars().all()
    my_counts = dict(
        (
            await session.execute(
                select(UserCoupon.coupon_id, func.count())
                .where(UserCoupon.user_id == user.id)
                .group_by(UserCoupon.coupon_id)
            )
        ).all()
    )
    data = []
    for c in rows:
        mine = my_counts.get(c.id, 0)
        sold_out = c.total > 0 and c.taken >= c.total
        data.append({
            "id": c.id, "name": c.name, "threshold": c.threshold, "amount": c.amount,
            "valid_days": c.valid_days, "valid_until": c.valid_until,
            "claimable": (not sold_out) and mine < c.per_user_limit,
            "sold_out": sold_out, "claimed": mine,
        })
    return Resp(data=data)


@router.post("/coupons/{coupon_id}/claim", response_model=Resp[dict])
async def claim(coupon_id: int, user: CurrentUser, session: DB):
    uc = await svc.claim(session, user, coupon_id)
    await session.commit()
    return Resp(data=svc.uc_to_dict(uc))


@router.get("/me/coupons", response_model=Resp[list[dict]])
async def my_coupons(user: CurrentUser, session: DB, status: str | None = None):
    """我的券。status 可选 unused/used/expired（expired 为惰性判定）。"""
    rows = await svc.list_my_coupons(session, user.id)
    data = [svc.uc_to_dict(uc) for uc in rows]
    if status:
        data = [d for d in data if d["status"] == status]
    return Resp(data=data)
