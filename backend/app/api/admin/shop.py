from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.deps import DB
from app.errors import BizError
from app.models.catalog import Category
from app.models.series import Series
from app.models.shop import ShopMenu
from app.schemas.admin import ShopMenuIn
from app.schemas.common import Resp
from app.services.shop import validate_banners

router = APIRouter()


def _row(m: ShopMenu) -> dict:
    return {"id": m.id, "kind": m.kind, "ref_id": m.ref_id, "title": m.title, "en": m.en,
            "banners": m.banners or [], "sort": m.sort, "status": m.status}


@router.get("/shop/menus", response_model=Resp[list[dict]])
async def list_menus(session: DB):
    """上部自定义项（已配置的）+ 下部一级类目（全量）。

    一级类目未配置过图片跳链时以 id=0 的占位行给出，管理端可直接编辑，
    首次保存时才真正落库——与固定挂载页的处理方式一致。
    """
    rows = (await session.execute(select(ShopMenu))).scalars().all()
    have = {(m.kind, m.ref_id) for m in rows}
    tops = (
        await session.execute(
            select(Category)
            .where(Category.parent_id.is_(None), Category.status == 1)
            .order_by(Category.sort, Category.id)
        )
    ).scalars().all()
    stubs = [
        ShopMenu(id=0, kind="category", ref_id=t.id, title="", en="", banners=[],
                 sort=t.sort, status=1)
        for t in tops if ("category", t.id) not in have
    ]
    order = {t.id: i for i, t in enumerate(tops)}
    out = [_row(m) for m in [*rows, *stubs]]
    # 自定义项在前（按自身 sort），一级类目在后（按品类树顺序）
    out.sort(key=lambda r: (0, r["sort"], r["id"]) if r["kind"] == "series"
             else (1, order.get(r["ref_id"], 999), 0))
    return Resp(data=out)


@router.put("/shop/menus", response_model=Resp[dict])
async def upsert_menu(req: ShopMenuIn, session: DB):
    """按 (kind, ref_id) 落库：不存在则新建，存在则更新。"""
    if req.kind == "series":
        if await session.get(Series, req.ref_id) is None:
            raise BizError("系列不存在")
    else:
        c = await session.get(Category, req.ref_id)
        if c is None or c.parent_id is not None:
            raise BizError("只能挂在一级类目上")
    validate_banners(req.banners)

    m = (
        await session.execute(
            select(ShopMenu).where(ShopMenu.kind == req.kind, ShopMenu.ref_id == req.ref_id)
        )
    ).scalar_one_or_none()
    if m is None:
        m = ShopMenu(kind=req.kind, ref_id=req.ref_id)
        session.add(m)
    m.title = req.title
    m.en = req.en
    m.banners = req.banners
    m.sort = req.sort
    m.status = req.status
    await session.commit()
    return Resp(data=_row(m))


@router.delete("/shop/menus/{menu_id}", response_model=Resp[None])
async def delete_menu(menu_id: int, session: DB):
    """只删自定义项；一级类目不可从菜单移除（在「品类管理」停用即可）。"""
    m = await session.get(ShopMenu, menu_id)
    if m is None:
        raise HTTPException(status_code=404, detail="菜单项不存在")
    if m.kind == "category":
        raise BizError("一级类目不可移除，请在「品类管理」停用")
    await session.delete(m)
    await session.commit()
    return Resp()
