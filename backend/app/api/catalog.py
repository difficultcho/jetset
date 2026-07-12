from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.deps import DB
from app.models.catalog import Category, Spu
from app.models.series import Series
from app.schemas.catalog import ProductDetail, ProductListItem
from app.schemas.common import Page, Resp
from app.services.catalog import spu_to_detail, spu_to_list_item

router = APIRouter()

SORTS = {
    "default": (Spu.sort.asc(), Spu.id.asc()),
    "sales": (Spu.sales.desc(), Spu.id.asc()),
    "price_asc": (Spu.price.asc(), Spu.id.asc()),
    "price_desc": (Spu.price.desc(), Spu.id.asc()),
    "newest": (Spu.created_at.desc(), Spu.id.desc()),
}


@router.get("/categories", response_model=Resp[list[dict]])
async def categories(session: DB):
    """品类树：一级含 children（二级）。"""
    rows = (
        await session.execute(
            select(Category).where(Category.status == 1).order_by(Category.sort, Category.id)
        )
    ).scalars().all()
    tops = [c for c in rows if c.parent_id is None]
    children: dict[int, list] = {}
    for c in rows:
        if c.parent_id is not None:
            children.setdefault(c.parent_id, []).append(c)
    return Resp(data=[
        {
            "id": t.id, "name": t.name, "en": t.en,
            "children": [{"id": s.id, "name": s.name, "en": s.en} for s in children.get(t.id, [])],
        }
        for t in tops
    ])


@router.get("/series", response_model=Resp[list[dict]])
async def series_list(session: DB):
    rows = (
        await session.execute(
            select(Series).where(Series.status == 1).order_by(Series.sort, Series.id)
        )
    ).scalars().all()
    return Resp(data=[
        {"id": s.id, "name": s.name, "en": s.en, "subtitle": s.subtitle,
         "cover_tint": s.cover_tint, "cover": s.cover}
        for s in rows
    ])


async def _category_ids(session, cat: str) -> list[int]:
    """按品类名匹配：命中一级则含其全部二级，命中二级则仅其自身。"""
    row = (
        await session.execute(select(Category).where(Category.name == cat, Category.status == 1))
    ).scalar_one_or_none()
    if row is None:
        return []
    ids = [row.id]
    if row.parent_id is None:
        subs = (
            await session.execute(select(Category.id).where(Category.parent_id == row.id))
        ).scalars().all()
        ids.extend(subs)
    return ids


@router.get("/products", response_model=Resp[Page[ProductListItem]])
async def products(
    session: DB,
    cat: str | None = None,
    series: int | None = None,
    q: str | None = None,
    sort: str = "default",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(Spu).where(Spu.status == 1)
    if cat:
        ids = await _category_ids(session, cat)
        if not ids:
            return Resp(data=Page(items=[], total=0, page=page, page_size=page_size))
        stmt = stmt.where(Spu.category_id.in_(ids))
    if series:
        stmt = stmt.where(Spu.series_id == series)
    if q:
        stmt = stmt.where(Spu.name.like(f"%{q}%"))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(*SORTS.get(sort, SORTS["default"]))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()

    # 批量取系列 en
    sids = {r.series_id for r in rows if r.series_id}
    series_en = {}
    if sids:
        for s in (await session.execute(select(Series).where(Series.id.in_(sids)))).scalars():
            series_en[s.id] = s.en
    return Resp(data=Page(
        items=[spu_to_list_item(s, series_en.get(s.series_id, "")) for s in rows],
        total=total, page=page, page_size=page_size,
    ))


@router.get("/products/{spu_id}", response_model=Resp[ProductDetail])
async def product_detail(spu_id: int, session: DB):
    spu = await session.get(Spu, spu_id)
    if spu is None or spu.status != 1:
        raise HTTPException(status_code=404, detail="商品不存在或已下架")
    series = None
    if spu.series_id:
        s = await session.get(Series, spu.series_id)
        if s:
            series = {"id": s.id, "name": s.name, "en": s.en, "subtitle": s.subtitle}
    return Resp(data=spu_to_detail(spu, series))
