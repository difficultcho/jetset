from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.deps import DB
from app.models.brand import BrandPost
from app.models.series import Series
from app.schemas.common import Resp

router = APIRouter()


def _card(p: BrandPost) -> dict:
    return {"id": p.id, "type": p.type, "title": p.title, "subtitle": p.subtitle,
            "cover": p.cover, "cover_tint": p.cover_tint, "link": p.link}


async def _with_detail(session, p: BrandPost) -> dict:
    """卡片 + 图文块 + 关联系列 + 子项目卡片。"""
    d = _card(p)
    d["body"] = p.body or []
    d["series"] = None
    if p.series_id:
        s = await session.get(Series, p.series_id)
        if s is not None:
            d["series"] = {"id": s.id, "name": s.name, "en": s.en}
    subs = (
        await session.execute(
            select(BrandPost).where(BrandPost.parent_id == p.id, BrandPost.status == 1)
            .order_by(BrandPost.sort, BrandPost.id)
        )
    ).scalars().all()
    d["sub_posts"] = [_card(x) for x in subs]
    return d


@router.get("/brand/posts", response_model=Resp[list[dict]])
async def list_posts(session: DB, type: str = Query(...), with_series: bool = False):
    """顶级帖列表；with_series=1 时只取关联了系列的（品牌 tab「系列」区块）。"""
    stmt = (
        select(BrandPost)
        .where(BrandPost.type == type, BrandPost.status == 1, BrandPost.parent_id.is_(None))
        .order_by(BrandPost.sort, BrandPost.id)
    )
    if with_series:
        stmt = stmt.where(BrandPost.series_id.isnot(None))
    rows = (await session.execute(stmt)).scalars().all()
    return Resp(data=[_card(p) for p in rows])


@router.get("/brand/series-posts", response_model=Resp[list[dict]])
async def series_posts(session: DB):
    """品牌 tab「系列」区块：任意类型、关联了系列的顶级帖。"""
    rows = (
        await session.execute(
            select(BrandPost)
            .where(BrandPost.status == 1, BrandPost.parent_id.is_(None),
                   BrandPost.series_id.isnot(None))
            .order_by(BrandPost.sort, BrandPost.id)
        )
    ).scalars().all()
    return Resp(data=[_card(p) for p in rows])


@router.get("/brand/posts/{post_id}", response_model=Resp[dict])
async def post_detail(post_id: int, session: DB):
    p = await session.get(BrandPost, post_id)
    if p is None or p.status != 1:
        raise HTTPException(status_code=404, detail="内容不存在")
    return Resp(data=await _with_detail(session, p))


@router.get("/brand/first", response_model=Resp[dict | None])
async def first_of_type(session: DB, type: str = Query(...)):
    """取某类型的首条顶级帖（moment/story/campaign 供品牌页直接进详情）。"""
    p = (
        await session.execute(
            select(BrandPost)
            .where(BrandPost.type == type, BrandPost.status == 1, BrandPost.parent_id.is_(None))
            .order_by(BrandPost.sort, BrandPost.id).limit(1)
        )
    ).scalar_one_or_none()
    if p is None:
        return Resp(data=None)
    return Resp(data=await _with_detail(session, p))
