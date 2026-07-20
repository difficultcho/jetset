"""配置化页面：块序列的保存校验与 C 端解析。

块结构（存储形态）：
  image    {kind, img, ratio('hero'=撑满首屏|'3/3.4'等), inset, link}
  video    {kind, src, poster, ratio, inset}            —— 视频不带链接
  text     {kind, preset('para'|'quote'|'eyebrow'|'link'), text, align, link}
  carousel {kind, source('featured'|'series'|'category'|'manual'),
            series_id, category_id, spu_ids, count}
链接结构：{kind: 'post'|'campaign'|'list'|'pdp', post_id|series_id|category_id|spu_id}
C 端解析后：carousel 块带 items（商品卡）；link 解析为可直接导航的参数（失效则为 None）。
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import BizError
from app.models.brand import BrandPost
from app.models.catalog import Category, Spu
from app.models.cms import Page
from app.models.series import Series
from app.services.catalog import spu_to_list_item

PAGE_KEYS = {"home"}
BLOCK_KINDS = {"image", "video", "text", "carousel"}
TEXT_PRESETS = {"para", "quote", "eyebrow", "link"}
CAROUSEL_SOURCES = {"featured", "series", "category", "manual"}
LINK_KINDS = {"post", "campaign", "list", "pdp"}


def validate_blocks(blocks: list) -> None:
    """保存时的结构校验（引用对象是否仍有效由 C 端解析兜底，不在此强校验）。"""
    for i, b in enumerate(blocks, 1):
        if not isinstance(b, dict) or b.get("kind") not in BLOCK_KINDS:
            raise BizError(f"第 {i} 块类型无效")
        if b["kind"] == "text" and b.get("preset") not in TEXT_PRESETS:
            raise BizError(f"第 {i} 块（文本）排版预设无效")
        if b["kind"] == "carousel":
            if b.get("source") not in CAROUSEL_SOURCES:
                raise BizError(f"第 {i} 块（走马灯）数据源无效")
            if b["source"] == "series" and not b.get("series_id"):
                raise BizError(f"第 {i} 块（走马灯）未选择系列")
            if b["source"] == "category" and not b.get("category_id"):
                raise BizError(f"第 {i} 块（走马灯）未选择品类")
            if b["source"] == "manual" and not b.get("spu_ids"):
                raise BizError(f"第 {i} 块（走马灯）未选择商品")
        link = b.get("link")
        if link is not None and b["kind"] != "video":
            if not isinstance(link, dict) or link.get("kind") not in LINK_KINDS:
                raise BizError(f"第 {i} 块跳转配置无效")


async def _carousel_items(session: AsyncSession, b: dict) -> list[dict]:
    count = min(max(int(b.get("count") or 6), 1), 10)
    stmt = select(Spu).where(Spu.status == 1)
    source = b.get("source")
    if source == "featured":
        stmt = stmt.where(Spu.featured.is_(True)).order_by(Spu.sort, Spu.id)
    elif source == "series":
        stmt = stmt.where(Spu.series_id == b.get("series_id")).order_by(Spu.sort, Spu.id)
    elif source == "category":
        cat_id = b.get("category_id")
        children = (
            await session.execute(select(Category.id).where(Category.parent_id == cat_id))
        ).scalars().all()
        stmt = stmt.where(Spu.category_id.in_([cat_id, *children])).order_by(Spu.sort, Spu.id)
    elif source == "manual":
        ids = [i for i in (b.get("spu_ids") or []) if isinstance(i, int)]
        if not ids:
            return []
        stmt = stmt.where(Spu.id.in_(ids))
    else:
        return []
    spus = (await session.execute(stmt.limit(count if source != "manual" else None))).scalars().all()
    if source == "manual":  # 保持手选顺序，已下架的自动剔除
        by_id = {s.id: s for s in spus}
        spus = [by_id[i] for i in ids if i in by_id][:count]

    # 卡片小字标用系列 en（与现有走马灯一致）
    sids = {s.series_id for s in spus if s.series_id}
    en_of = {}
    if sids:
        rows = (await session.execute(select(Series).where(Series.id.in_(sids)))).scalars().all()
        en_of = {s.id: s.en for s in rows}
    return [spu_to_list_item(s, en_of.get(s.series_id, "")) for s in spus]


async def _resolve_link(session: AsyncSession, link) -> dict | None:
    """把存储态链接解析成小程序可直接导航的参数；目标失效返回 None（块不可点）。"""
    if not isinstance(link, dict) or link.get("kind") not in LINK_KINDS:
        return None
    kind = link["kind"]
    if kind == "campaign":
        return {"kind": "campaign"}
    if kind == "post":
        p = await session.get(BrandPost, link.get("post_id") or 0)
        return {"kind": "post", "post_id": p.id} if p is not None and p.status == 1 else None
    if kind == "pdp":
        s = await session.get(Spu, link.get("spu_id") or 0)
        return {"kind": "pdp", "spu_id": s.id} if s is not None and s.status == 1 else None
    # list：解析出列表页需要的过滤参数与标题
    out: dict = {"kind": "list", "title": ""}
    if link.get("category_id"):
        c = await session.get(Category, link["category_id"])
        if c is None or c.status != 1:
            return None
        out["cat"] = c.name
        out["title"] = c.name
    elif link.get("series_id"):
        s = await session.get(Series, link["series_id"])
        if s is None or s.status != 1:
            return None
        out["series"] = s.id
        out["title"] = s.en or s.name
    return out


async def resolve_page(session: AsyncSession, key: str) -> dict | None:
    """C 端页面解析；未配置/停用/空块返回 None（小程序回落默认排版）。"""
    page = await session.get(Page, key)
    if page is None or page.status != 1 or not page.blocks:
        return None
    blocks = []
    for b in page.blocks:
        if not isinstance(b, dict) or b.get("kind") not in BLOCK_KINDS:
            continue
        rb = dict(b)
        # 内容为空的块直接剔除，客户端不渲染空盒子
        if rb["kind"] == "image" and not rb.get("img"):
            continue
        if rb["kind"] == "video" and not rb.get("src"):
            continue
        if rb["kind"] == "text" and not (rb.get("text") or "").strip():
            continue
        if rb["kind"] == "carousel":
            rb["items"] = await _carousel_items(session, rb)
            if not rb["items"]:
                continue
        rb["link"] = await _resolve_link(session, rb.get("link")) if rb["kind"] != "video" else None
        blocks.append(rb)
    return {"key": key, "blocks": blocks}
