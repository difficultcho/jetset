"""商城配置：左菜单的保存校验与 C 端解析。

左菜单两组：
  上部  自定义项（当前支持「系列」），由 shop_menu 表定义
  下部  一级类目，由品类树派生；shop_menu 只为其附加图片跳链

每个菜单项选中后，右侧分两部分：
  banners  图片跳链，固定尺寸依次罗列，图下可带一行左对齐文字标题（title，可空）；
           目的地复用页面体系的链接（page/list/pdp）
  entries  下钻入口。下钻「逻辑」按菜单项类型不同，但「产物」统一是一个商品列表过滤条件：
             一级类目 → 它的子类目        filter {cat: 子类目名}，并带 image
             系列     → 该系列涉及的一级类目 filter {series: id, cat: 一级名}
           子类目的 image 是该类目下综合排序第一个上架商品的首图；没有商品或没有图则为 null。
           小程序据此把子类画成两列方块。没建子类目时 entries 恒为空，
           「全部XX」不是方块，由小程序放在上部图片跳链那一区。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import BizError
from app.models.catalog import Category, Spu
from app.models.series import Series
from app.models.shop import ShopMenu
from app.services.catalog import _first_image
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
    """系列涉及的一级类目：由在售商品的类目归属去重派生，无需人工维护。

    归并规则：有父级的归到父级，没父级的（本身就是叶子的一级类目）归到它自己。
    不是所有品类都会细分出二级，所以「商品挂在一级类目上」是常规情况。
    早期实现只认 parent_id 非空的类目，把这类商品整个丢掉，导致系列右侧一片空白。
    """
    cat_ids = (
        await session.execute(
            select(Spu.category_id).where(Spu.series_id == series_id, Spu.status == 1).distinct()
        )
    ).scalars().all()
    if not cat_ids:
        return []
    owned = (
        await session.execute(select(Category).where(Category.id.in_(cat_ids)))
    ).scalars().all()
    top_ids = {c.parent_id if c.parent_id is not None else c.id for c in owned}
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


async def _child_cover_images(session: AsyncSession, child_ids: list[int]) -> dict[int, str | None]:
    """每个子类目一张封面：sort、id 升序下第一个上架商品的首图。

    第一个商品没有图时不往后找，与「第一个商品的第一张图」一致。没有上架商品则为 None。
    """
    covers: dict[int, str | None] = {cid: None for cid in child_ids}
    if not child_ids:
        return covers
    rows = (
        await session.execute(
            select(Spu.id, Spu.category_id, Spu.sort).where(
                Spu.status == 1, Spu.category_id.in_(child_ids)
            )
        )
    ).all()
    winner: dict[int, tuple[int, int]] = {}
    for spu_id, category_id, sort in rows:
        cand = (sort, spu_id)
        cur = winner.get(category_id)
        if cur is None or cand < cur:
            winner[category_id] = cand
    if not winner:
        return covers
    spus = {
        spu.id: spu
        for spu in (
            await session.execute(
                select(Spu).where(Spu.id.in_([spu_id for _sort, spu_id in winner.values()]))
            )
        ).scalars()
    }
    for cid, (_sort, spu_id) in winner.items():
        covers[cid] = _first_image(spus[spu_id])
    return covers


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
    covers = await _child_cover_images(
        session, [s.id for subs in children.values() for s in subs]
    )
    for t in [c for c in cats if c.parent_id is None]:
        r = by_ref.get(("category", t.id))
        entries = [
            {
                "title": s.name, "en": s.en, "filter": {"cat": s.name},
                "image": covers.get(s.id),
            }
            for s in children.get(t.id, [])
        ]
        menus.append({
            "key": f"cat-{t.id}", "kind": "category", "id": t.id,
            "title": (r.title if r and r.title else t.name), "en": (r.en if r and r.en else t.en),
            "filter": {"cat": t.name},
            "banners": await _banners(session, r), "entries": entries,
        })

    return {"menus": menus}
