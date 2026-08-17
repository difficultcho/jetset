"""商城配置：左菜单的保存校验与 C 端解析。

左菜单两组：
  上部  自定义项（当前支持「系列」），由 shop_menu 表定义
  下部  一级类目，由品类树派生；shop_menu 只为其附加图片跳链

每个菜单项选中后，右侧分两部分：
  banners  图片跳链，固定尺寸依次罗列，图下可带一行左对齐文字标题（title，可空）；
           目的地复用页面体系的链接（page/list/pdp）
  entries  下钻入口。下钻「逻辑」按菜单项类型不同，但「产物」统一是一个商品列表过滤条件：
             一级类目 → 它的二级类目      filter {cat: 二级名}
             系列     → 该系列涉及的一级类目 filter {series: id, cat: 一级名}
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import BizError
from app.models.catalog import Category, Spu
from app.models.series import Series
from app.models.shop import ShopMenu
from app.services.pages import LINK_KINDS, _resolve_link

MENU_KINDS = {"series", "category"}


BANNER_TITLE_MAX = 60


def validate_banners(banners: list) -> None:
    """保存时的结构校验（引用对象是否仍有效由 C 端解析兜底）。"""
    if not isinstance(banners, list):
        raise BizError("图片跳链格式无效")
    for i, b in enumerate(banners, 1):
        if not isinstance(b, dict) or not (b.get("img") or "").strip():
            raise BizError(f"第 {i} 张图片未上传")
        title = b.get("title") or ""
        if not isinstance(title, str):
            raise BizError(f"第 {i} 张图片的文字标题格式无效")
        if len(title.strip()) > BANNER_TITLE_MAX:
            raise BizError(f"第 {i} 张图片的文字标题不能超过 {BANNER_TITLE_MAX} 字")
        link = b.get("link")
        if link is not None and (not isinstance(link, dict) or link.get("kind") not in LINK_KINDS):
            raise BizError(f"第 {i} 张图片跳转配置无效")


async def _series_top_categories(session: AsyncSession, series_id: int) -> list[Category]:
    """系列涉及的一级类目：由在售商品的二级类目归属去重派生，无需人工维护。"""
    leaf_ids = (
        await session.execute(
            select(Spu.category_id).where(Spu.series_id == series_id, Spu.status == 1).distinct()
        )
    ).scalars().all()
    if not leaf_ids:
        return []
    leaves = (
        await session.execute(select(Category).where(Category.id.in_(leaf_ids)))
    ).scalars().all()
    top_ids = {c.parent_id for c in leaves if c.parent_id is not None}
    if not top_ids:
        return []
    return (
        await session.execute(
            select(Category)
            .where(Category.id.in_(top_ids), Category.status == 1)
            .order_by(Category.sort, Category.id)
        )
    ).scalars().all()


async def _banners(session: AsyncSession, row: ShopMenu | None) -> list[dict]:
    if row is None or not row.banners:
        return []
    out = []
    for b in row.banners:
        if not isinstance(b, dict) or not b.get("img"):
            continue
        out.append({
            "img": b["img"],
            "title": (b.get("title") or "").strip(),   # 图片下方的文字标题，可为空
            "link": await _resolve_link(session, b.get("link")),
        })
    return out


async def resolve_shop(session: AsyncSession) -> dict:
    """C 端商城骨架：左菜单 + 每项的图片跳链与下钻入口。"""
    rows = (await session.execute(select(ShopMenu))).scalars().all()
    by_ref = {(r.kind, r.ref_id): r for r in rows}
    menus: list[dict] = []

    # 上部：自定义项（系列）——顺序与上下架由 shop_menu 自己定
    tops = sorted(
        [r for r in rows if r.kind == "series" and r.status == 1],
        key=lambda r: (r.sort, r.id),
    )
    if tops:
        series_map = {
            s.id: s
            for s in (
                await session.execute(
                    select(Series).where(
                        Series.id.in_([r.ref_id for r in tops]), Series.status == 1
                    )
                )
            ).scalars()
        }
        for r in tops:
            s = series_map.get(r.ref_id)
            if s is None:  # 系列被删/停用 → 该菜单项自动隐藏
                continue
            entries = [
                {"title": c.name, "en": c.en, "filter": {"series": s.id, "cat": c.name}}
                for c in await _series_top_categories(session, s.id)
            ]
            menus.append({
                "key": f"series-{s.id}", "kind": "series", "id": s.id,
                "title": r.title or s.name, "en": r.en or s.en,
                "filter": {"series": s.id},
                "banners": await _banners(session, r), "entries": entries,
            })

    # 下部：一级类目——名称/排序/上下架以品类管理为准
    cats = (
        await session.execute(
            select(Category).where(Category.status == 1).order_by(Category.sort, Category.id)
        )
    ).scalars().all()
    children: dict[int, list[Category]] = {}
    for c in cats:
        if c.parent_id is not None:
            children.setdefault(c.parent_id, []).append(c)
    for t in [c for c in cats if c.parent_id is None]:
        r = by_ref.get(("category", t.id))
        entries = [
            {"title": s.name, "en": s.en, "filter": {"cat": s.name}} for s in children.get(t.id, [])
        ]
        menus.append({
            "key": f"cat-{t.id}", "kind": "category", "id": t.id,
            "title": (r.title if r and r.title else t.name), "en": (r.en if r and r.en else t.en),
            "filter": {"cat": t.name},
            "banners": await _banners(session, r), "entries": entries,
        })

    return {"menus": menus}
