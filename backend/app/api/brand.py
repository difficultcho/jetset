from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.deps import DB
from app.models.brand import BrandPost
from app.schemas.common import Resp

router = APIRouter()


def _card(p: BrandPost) -> dict:
    return {"id": p.id, "type": p.type, "title": p.title, "subtitle": p.subtitle,
            "cover": p.cover, "cover_tint": p.cover_tint, "link": p.link}


@router.get("/brand/posts", response_model=Resp[list[dict]])
async def list_posts(session: DB, type: str = Query(...)):
    rows = (
        await session.execute(
            select(BrandPost).where(BrandPost.type == type, BrandPost.status == 1)
            .order_by(BrandPost.sort, BrandPost.id)
        )
    ).scalars().all()
    return Resp(data=[_card(p) for p in rows])


@router.get("/brand/posts/{post_id}", response_model=Resp[dict])
async def post_detail(post_id: int, session: DB):
    p = await session.get(BrandPost, post_id)
    if p is None or p.status != 1:
        raise HTTPException(status_code=404, detail="内容不存在")
    d = _card(p)
    d["body"] = p.body or []
    return Resp(data=d)


@router.get("/brand/first", response_model=Resp[dict | None])
async def first_of_type(session: DB, type: str = Query(...)):
    """取某类型的首条（moment/story/campaign 各一条，供品牌页直接进详情）。"""
    p = (
        await session.execute(
            select(BrandPost).where(BrandPost.type == type, BrandPost.status == 1)
            .order_by(BrandPost.sort, BrandPost.id).limit(1)
        )
    ).scalar_one_or_none()
    if p is None:
        return Resp(data=None)
    d = _card(p)
    d["body"] = p.body or []
    return Resp(data=d)
