from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.deps import DB
from app.errors import BizError
from app.models.wholesale import WholesaleApplication
from app.schemas.admin import ReviewReq
from app.schemas.common import Page, Resp

router = APIRouter()


def _row(a: WholesaleApplication) -> dict:
    return {
        "id": a.id, "user_id": a.user_id, "type": a.type, "phone": a.phone,
        "company": a.company, "region": a.region, "license_img": a.license_img,
        "store_img": a.store_img, "status": a.status, "review_note": a.review_note,
        "created_at": a.created_at,
    }


@router.get("/wholesale", response_model=Resp[Page[dict]])
async def list_applications(
    session: DB,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(WholesaleApplication)
    if status:
        stmt = stmt.where(WholesaleApplication.status == status)
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await session.execute(
            stmt.order_by(WholesaleApplication.id.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()
    return Resp(data=Page(items=[_row(a) for a in rows], total=total, page=page, page_size=page_size))


@router.post("/wholesale/{app_id}/review", response_model=Resp[dict])
async def review(app_id: int, req: ReviewReq, session: DB):
    row = await session.get(WholesaleApplication, app_id)
    if row is None:
        raise HTTPException(status_code=404, detail="申请不存在")
    if row.status != "pending":
        raise BizError("该申请已处理")
    row.status = "approved" if req.action == "approve" else "rejected"
    row.review_note = req.note
    await session.commit()
    # TODO: 订阅消息通知申请人审核结果
    return Resp(data={"id": row.id, "status": row.status})
