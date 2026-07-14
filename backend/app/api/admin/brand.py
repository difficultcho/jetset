from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.deps import DB
from app.models.brand import BrandPost
from app.models.series import Series
from app.schemas.admin import BrandPostIn
from app.schemas.common import Resp

router = APIRouter()


def _row(p: BrandPost) -> dict:
    return {"id": p.id, "type": p.type, "title": p.title, "subtitle": p.subtitle,
            "cover": p.cover, "cover_tint": p.cover_tint, "body": p.body or [],
            "series_id": p.series_id, "parent_id": p.parent_id,
            "link": p.link, "sort": p.sort, "status": p.status}


async def _check_refs(session, req: BrandPostIn, post_id: int | None = None) -> None:
    if req.series_id is not None and await session.get(Series, req.series_id) is None:
        raise HTTPException(status_code=400, detail="关联系列不存在")
    if req.parent_id is not None:
        if post_id is not None and req.parent_id == post_id:
            raise HTTPException(status_code=400, detail="不能以自己为父项目")
        parent = await session.get(BrandPost, req.parent_id)
        if parent is None:
            raise HTTPException(status_code=400, detail="父项目不存在")
        if parent.parent_id is not None:
            raise HTTPException(status_code=400, detail="活动项目最多两级")


@router.get("/brand/posts", response_model=Resp[list[dict]])
async def list_posts(session: DB, type: str | None = None):
    stmt = select(BrandPost).order_by(BrandPost.sort, BrandPost.id)
    if type:
        stmt = stmt.where(BrandPost.type == type)
    rows = (await session.execute(stmt)).scalars().all()
    return Resp(data=[_row(p) for p in rows])


@router.post("/brand/posts", response_model=Resp[dict])
async def create_post(req: BrandPostIn, session: DB):
    await _check_refs(session, req)
    p = BrandPost(**req.model_dump())
    session.add(p)
    await session.commit()
    return Resp(data=_row(p))


@router.put("/brand/posts/{post_id}", response_model=Resp[dict])
async def update_post(post_id: int, req: BrandPostIn, session: DB):
    p = await session.get(BrandPost, post_id)
    if p is None:
        raise HTTPException(status_code=404, detail="内容不存在")
    await _check_refs(session, req, post_id)
    for field, value in req.model_dump().items():
        setattr(p, field, value)
    await session.commit()
    return Resp(data=_row(p))


@router.delete("/brand/posts/{post_id}", response_model=Resp[None])
async def delete_post(post_id: int, session: DB):
    p = await session.get(BrandPost, post_id)
    if p is None:
        raise HTTPException(status_code=404, detail="内容不存在")
    children = (
        await session.execute(select(func.count()).where(BrandPost.parent_id == post_id))
    ).scalar_one()
    if children:
        raise HTTPException(status_code=400, detail=f"该项目下有 {children} 个子项目，请先处理")
    await session.delete(p)
    await session.commit()
    return Resp()
