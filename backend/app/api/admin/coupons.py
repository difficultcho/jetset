from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select

from app.deps import DB
from app.models.coupon import Coupon, UserCoupon
from app.schemas.admin import StatusReq
from app.schemas.common import Resp

router = APIRouter()


class CouponIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    threshold: int = Field(default=0, ge=0)   # 分
    amount: int = Field(ge=1)                 # 分
    total: int = Field(default=0, ge=0)       # 0=不限量
    per_user_limit: int = Field(default=1, ge=1)
    valid_days: int | None = Field(default=None, ge=1)
    valid_until: datetime | None = None
    status: int = Field(default=1, ge=0, le=1)

    @model_validator(mode="after")
    def check_validity(self):
        if self.valid_days is None and self.valid_until is None:
            raise ValueError("valid_days 与 valid_until 至少配置一个")
        if self.threshold and self.amount >= self.threshold:
            raise ValueError("减免金额不应大于等于使用门槛")
        return self


def _row(c: Coupon, used: int = 0) -> dict:
    return {
        "id": c.id, "name": c.name, "threshold": c.threshold, "amount": c.amount,
        "total": c.total, "taken": c.taken, "used": used,
        "per_user_limit": c.per_user_limit, "valid_days": c.valid_days,
        "valid_until": c.valid_until, "status": c.status, "created_at": c.created_at,
    }


@router.get("/coupons", response_model=Resp[list[dict]])
async def list_coupons(session: DB):
    rows = (
        await session.execute(select(Coupon).order_by(Coupon.id.desc()))
    ).scalars().all()
    used_counts = dict(
        (
            await session.execute(
                select(UserCoupon.coupon_id, func.count())
                .where(UserCoupon.status == "used")
                .group_by(UserCoupon.coupon_id)
            )
        ).all()
    )
    return Resp(data=[_row(c, used_counts.get(c.id, 0)) for c in rows])


@router.post("/coupons", response_model=Resp[dict])
async def create_coupon(req: CouponIn, session: DB):
    c = Coupon(**req.model_dump())
    session.add(c)
    await session.commit()
    return Resp(data=_row(c))


@router.put("/coupons/{coupon_id}", response_model=Resp[dict])
async def update_coupon(coupon_id: int, req: CouponIn, session: DB):
    c = await session.get(Coupon, coupon_id)
    if c is None:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    # 已领的券是快照，改模板只影响后续领取
    for field, value in req.model_dump().items():
        setattr(c, field, value)
    await session.commit()
    return Resp(data=_row(c))


@router.post("/coupons/{coupon_id}/status", response_model=Resp[dict])
async def toggle_coupon(coupon_id: int, req: StatusReq, session: DB):
    c = await session.get(Coupon, coupon_id)
    if c is None:
        raise HTTPException(status_code=404, detail="优惠券不存在")
    c.status = req.status
    await session.commit()
    return Resp(data={"id": c.id, "status": c.status})
