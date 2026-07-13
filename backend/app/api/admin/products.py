from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import DB
from app.models.catalog import Category, Sku, Spu, SpuImage
from app.models.series import Series
from app.schemas.admin import CategoryIn, ProductIn, StatusReq
from app.schemas.common import Page, Resp

router = APIRouter()


async def _check_parent(session: AsyncSession, parent_id: int | None) -> None:
    if parent_id is None:
        return
    parent = await session.get(Category, parent_id)
    if parent is None:
        raise HTTPException(status_code=400, detail="父级品类不存在")
    if parent.parent_id is not None:
        raise HTTPException(status_code=400, detail="品类最多两级")


@router.get("/categories", response_model=Resp[list[dict]])
async def list_categories(session: DB):
    """全量品类（含父子关系），供商品表单级联选择。"""
    rows = (await session.execute(select(Category).order_by(Category.sort, Category.id))).scalars().all()
    name_of = {c.id: c.name for c in rows}
    return Resp(data=[
        {
            "id": c.id, "name": c.name, "en": c.en, "parent_id": c.parent_id,
            "parent_name": name_of.get(c.parent_id), "status": c.status,
        }
        for c in rows
    ])


@router.post("/categories", response_model=Resp[dict])
async def create_category(req: CategoryIn, session: DB):
    await _check_parent(session, req.parent_id)
    c = Category(**req.model_dump())
    session.add(c)
    await session.commit()
    return Resp(data={"id": c.id, "name": c.name, "parent_id": c.parent_id})


@router.put("/categories/{cat_id}", response_model=Resp[dict])
async def update_category(cat_id: int, req: CategoryIn, session: DB):
    c = await session.get(Category, cat_id)
    if c is None:
        raise HTTPException(status_code=404, detail="品类不存在")
    if req.parent_id is not None:
        if req.parent_id == cat_id:
            raise HTTPException(status_code=400, detail="不能以自己为父级")
        has_children = (
            await session.execute(
                select(func.count()).where(Category.parent_id == cat_id)
            )
        ).scalar_one()
        if has_children:
            raise HTTPException(status_code=400, detail="该品类下有子级，不能改为二级")
    await _check_parent(session, req.parent_id)
    for field, value in req.model_dump().items():
        setattr(c, field, value)
    await session.commit()
    return Resp(data={"id": c.id, "name": c.name, "parent_id": c.parent_id, "status": c.status})


def _sku_dict(s: Sku) -> dict:
    return {
        "id": s.id, "color_index": s.color_index, "color_name": s.color_name,
        "color_hex": s.color_hex, "size": s.size, "price": s.price,
        "stock": s.stock, "status": s.status,
    }


def _refresh_spu_price(spu: Spu) -> None:
    active = [s.price for s in spu.skus if s.status == 1]
    if active:
        spu.price = min(active)


async def _apply_skus(session: AsyncSession, spu: Spu, skus_in: list,
                      existing_skus: list[Sku]) -> None:
    """按自然键（color_index, size）对齐 SKU：有则更新、无则新建、缺则停售。

    existing_skus 由调用方显式传入（新建传空列表），避免在异步上下文外触发懒加载。
    """
    existing = {(s.color_index, s.size): s for s in existing_skus}
    incoming_keys = set()
    for si in skus_in:
        key = (si.color_index, si.size)
        incoming_keys.add(key)
        if key in existing:
            row = existing[key]
            row.color_name, row.color_hex = si.color_name, si.color_hex
            row.price, row.stock, row.status = si.price, si.stock, si.status
        else:
            session.add(Sku(
                spu_id=spu.id, color_index=si.color_index, color_name=si.color_name,
                color_hex=si.color_hex, size=si.size, price=si.price,
                stock=si.stock, status=si.status,
            ))
    for key, row in existing.items():
        if key not in incoming_keys:
            row.status = 0  # 历史订单引用 SKU，不物理删除


async def _apply_images(session: AsyncSession, spu_id: int, images_in: list) -> None:
    await session.execute(delete(SpuImage).where(SpuImage.spu_id == spu_id))
    for img in images_in:
        session.add(SpuImage(spu_id=spu_id, color_index=img.color_index,
                             url=img.url, sort=img.sort))


@router.get("/products", response_model=Resp[Page[dict]])
async def list_products(
    session: DB,
    q: str | None = None,
    status: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    stmt = select(Spu, Category.name).join(Category, Spu.category_id == Category.id)
    if q:
        stmt = stmt.where(Spu.name.like(f"%{q}%") | Spu.code.like(f"%{q}%"))
    if status is not None:
        stmt = stmt.where(Spu.status == status)
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await session.execute(
            stmt.order_by(Spu.sort, Spu.id).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    items = [
        {
            "id": spu.id, "name": spu.name, "sub": spu.sub, "code": spu.code,
            "category_id": spu.category_id, "category_name": cat_name,
            "series_id": spu.series_id,
            "price": spu.price, "sales": spu.sales, "badge": spu.badge,
            "featured": spu.featured, "sort": spu.sort, "status": spu.status,
            "sku_count": len([s for s in spu.skus if s.status == 1]),
            "stock_total": sum(s.stock for s in spu.skus if s.status == 1),
        }
        for spu, cat_name in rows
    ]
    return Resp(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/products/{spu_id}", response_model=Resp[dict])
async def get_product(spu_id: int, session: DB):
    spu = await session.get(Spu, spu_id)
    if spu is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return Resp(data={
        "id": spu.id, "category_id": spu.category_id, "series_id": spu.series_id,
        "name": spu.name, "sub": spu.sub, "code": spu.code,
        "en_model": spu.en_model, "brief": spu.brief, "detail": spu.detail,
        "bullets": spu.bullets or [], "has_video": spu.has_video,
        "original_price": spu.original_price,
        "badge": spu.badge, "featured": spu.featured, "sort": spu.sort,
        "status": spu.status, "price": spu.price,
        "skus": [_sku_dict(s) for s in sorted(spu.skus, key=lambda x: (x.color_index, x.id))],
        "images": [
            {"id": i.id, "color_index": i.color_index, "url": i.url, "sort": i.sort}
            for i in spu.images
        ],
    })


async def _check_refs(session: AsyncSession, req: ProductIn) -> None:
    if await session.get(Category, req.category_id) is None:
        raise HTTPException(status_code=400, detail="分类不存在")
    if req.series_id is not None and await session.get(Series, req.series_id) is None:
        raise HTTPException(status_code=400, detail="系列不存在")


@router.post("/products", response_model=Resp[dict])
async def create_product(req: ProductIn, session: DB):
    await _check_refs(session, req)
    spu = Spu(
        category_id=req.category_id, series_id=req.series_id,
        name=req.name, sub=req.sub, en_model=req.en_model, code=req.code,
        brief=req.brief, detail=req.detail, bullets=req.bullets or None,
        badge=req.badge, featured=req.featured, has_video=req.has_video,
        original_price=req.original_price, sort=req.sort, status=req.status,
    )
    session.add(spu)
    await session.flush()
    await _apply_skus(session, spu, req.skus, [])
    await _apply_images(session, spu.id, req.images)
    await session.flush()
    await session.refresh(spu, ["skus"])
    _refresh_spu_price(spu)
    await session.commit()
    return Resp(data={"id": spu.id})


@router.put("/products/{spu_id}", response_model=Resp[dict])
async def update_product(spu_id: int, req: ProductIn, session: DB):
    spu = await session.get(Spu, spu_id)
    if spu is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    await _check_refs(session, req)
    spu.category_id, spu.series_id = req.category_id, req.series_id
    spu.name, spu.sub, spu.en_model, spu.code = req.name, req.sub, req.en_model, req.code
    spu.brief, spu.detail, spu.bullets = req.brief, req.detail, (req.bullets or None)
    spu.badge, spu.has_video, spu.original_price = req.badge, req.has_video, req.original_price
    spu.featured, spu.sort, spu.status = req.featured, req.sort, req.status
    await _apply_skus(session, spu, req.skus, list(spu.skus))
    await _apply_images(session, spu.id, req.images)
    await session.flush()
    await session.refresh(spu, ["skus"])
    _refresh_spu_price(spu)
    await session.commit()
    return Resp(data={"id": spu.id})


@router.post("/products/{spu_id}/status", response_model=Resp[dict])
async def toggle_status(spu_id: int, req: StatusReq, session: DB):
    spu = await session.get(Spu, spu_id)
    if spu is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    spu.status = req.status
    await session.commit()
    return Resp(data={"id": spu.id, "status": spu.status})
