from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.deps import DB
from app.models.user import User
from app.schemas.admin import StatusReq
from app.schemas.common import Page, Resp

router = APIRouter()


@router.get("/users", response_model=Resp[Page[dict]])
async def list_users(
    session: DB,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(User)
    if q:
        stmt = stmt.where(User.name.like(f"%{q}%") | User.phone.like(f"%{q}%"))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await session.execute(
            stmt.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    items = [
        {
            "id": u.id, "name": u.name, "phone": u.phone,
            "openid": (u.openid[:8] + "***") if u.openid else "",
            "points": u.points, "status": u.status, "created_at": u.created_at,
        }
        for u in rows
    ]
    return Resp(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.put("/users/{user_id}/status", response_model=Resp[dict])
async def toggle_user(user_id: int, req: StatusReq, session: DB):
    u = await session.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.status = req.status
    await session.commit()
    return Resp(data={"id": u.id, "status": u.status})
