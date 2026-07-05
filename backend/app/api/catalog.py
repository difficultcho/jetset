from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.deps import DB
from app.models.catalog import Category, Spu
from app.schemas.catalog import CategoryOut, ProductDetail, ProductListItem
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


@router.get("/categories", response_model=Resp[list[CategoryOut]])
async def categories(session: DB):
    rows = (
        await session.execute(
            select(Category).where(Category.status == 1).order_by(Category.sort, Category.id)
        )
    ).scalars().all()
    return Resp(data=[CategoryOut.model_validate(c) for c in rows])


@router.get("/products", response_model=Resp[Page[ProductListItem]])
async def products(
    session: DB,
    cat: str | None = None,
    q: str | None = None,
    sort: str = "default",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(Spu).where(Spu.status == 1)
    if cat:
        stmt = stmt.join(Category, Spu.category_id == Category.id).where(Category.name == cat)
    if q:
        stmt = stmt.where(Spu.name.like(f"%{q}%"))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(*SORTS.get(sort, SORTS["default"]))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return Resp(data=Page(
        items=[spu_to_list_item(s) for s in rows],
        total=total, page=page, page_size=page_size,
    ))


@router.get("/products/{spu_id}", response_model=Resp[ProductDetail])
async def product_detail(spu_id: int, session: DB):
    spu = await session.get(Spu, spu_id)
    if spu is None or spu.status != 1:
        raise HTTPException(status_code=404, detail="商品不存在或已下架")
    return Resp(data=spu_to_detail(spu))
