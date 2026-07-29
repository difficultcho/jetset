from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.deps import DB
from app.models.catalog import Category, Sku, Spu
from app.models.series import Series
from app.schemas.catalog import ProductDetail, ProductListItem
from app.schemas.common import Page, Resp
from app.services.catalog import spu_to_detail, spu_to_list_item

router = APIRouter()

# 尺码展示序（库里是自由文本，按服装惯例排；未知值排在最后）
SIZE_ORDER = ["均码", "XS", "S", "M", "L", "XL", "XXL", "XXXL"]

# 价格档位（分）。写死在这里而不是查库：档位是运营口径，不该随数据漂移
PRICE_RANGES = [
    (0, 199999, "¥2,000 以下"),
    (200000, 499999, "¥2,000 - 5,000"),
    (500000, 999999, "¥5,000 - 10,000"),
    (1000000, 99999999, "¥10,000 以上"),
]

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


@router.get("/products/filters", response_model=Resp[dict])
async def product_filters(session: DB):
    """筛选项。与当前结果集无关（不做 faceting），一次全局查询即可，分页/上拉不受影响。
    代价是可能筛出空列表——正常电商行为，比每页扫全集划算。"""
    sizes = (
        await session.execute(select(Sku.size).where(Sku.status == 1, Sku.size != "").distinct())
    ).scalars().all()
    ordered = sorted(sizes, key=lambda s: (SIZE_ORDER.index(s) if s in SIZE_ORDER else 99, s))
    groups = []
    if ordered:
        groups.append({"key": "size", "t": "尺码", "multi": True,
                       "opts": [{"v": s, "label": s} for s in ordered]})
    groups.append({"key": "price", "t": "价格", "multi": False,
                   "opts": [{"v": f"{lo}-{hi}", "label": label} for lo, hi, label in PRICE_RANGES]})
    return Resp(data={"groups": groups})


@router.get("/products", response_model=Resp[Page[ProductListItem]])
async def products(
    session: DB,
    cat: str | None = None,
    series: int | None = None,
    q: str | None = None,
    featured: bool = False,
    size: str | None = None,        # 多选，逗号分隔
    price_min: int | None = None,   # 分
    price_max: int | None = None,
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
    if featured:
        stmt = stmt.where(Spu.featured.is_(True))
    if size:
        wanted = [s for s in (x.strip() for x in size.split(",")) if s]
        if wanted:
            stmt = stmt.where(
                select(Sku.id)
                .where(Sku.spu_id == Spu.id, Sku.status == 1, Sku.size.in_(wanted))
                .exists()
            )
    if price_min is not None:
        stmt = stmt.where(Spu.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(Spu.price <= price_max)
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
    cat = await session.get(Category, spu.category_id)
    return Resp(data=spu_to_detail(spu, series, cat.name if cat else ""))
