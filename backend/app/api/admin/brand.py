from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.deps import DB
from app.models.brand import BrandPost
from app.schemas.admin import BrandPostIn
from app.schemas.common import Resp

router = APIRouter()


def _row(p: BrandPost) -> dict:
    return {"id": p.id, "type": p.type, "title": p.title, "subtitle": p.subtitle,
            "cover": p.cover, "cover_tint": p.cover_tint, "body": p.body or [],
            "link": p.link, "sort": p.sort, "status": p.status}


@router.get("/brand/posts", response_model=Resp[list[dict]])
async def list_posts(session: DB, type: str | None = None):
    stmt = select(BrandPost).order_by(BrandPost.sort, BrandPost.id)
    if type:
        stmt = stmt.where(BrandPost.type == type)
    rows = (await session.execute(stmt)).scalars().all()
    return Resp(data=[_row(p) for p in rows])


@router.post("/brand/posts", response_model=Resp[dict])
async def create_post(req: BrandPostIn, session: DB):
    p = BrandPost(**req.model_dump())
    session.add(p)
    await session.commit()
    return Resp(data=_row(p))


@router.put("/brand/posts/{post_id}", response_model=Resp[dict])
async def update_post(post_id: int, req: BrandPostIn, session: DB):
    p = await session.get(BrandPost, post_id)
    if p is None:
        raise HTTPException(status_code=404, detail="内容不存在")
    for field, value in req.model_dump().items():
        setattr(p, field, value)
    await session.commit()
    return Resp(data=_row(p))


@router.delete("/brand/posts/{post_id}", response_model=Resp[None])
async def delete_post(post_id: int, session: DB):
    p = await session.get(BrandPost, post_id)
    if p is None:
        raise HTTPException(status_code=404, detail="内容不存在")
    await session.delete(p)
    await session.commit()
    return Resp()
