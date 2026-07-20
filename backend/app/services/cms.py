"""全站配置与首页视频位解析。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import BrandPost
from app.models.cms import Setting
from app.models.series import Series

HOME_VIDEO_KEY = "home_video_series_id"


async def get_setting(session: AsyncSession, key: str) -> str:
    row = await session.get(Setting, key)
    return row.value if row else ""


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    """写入配置（不 commit，由调用方统一提交）。"""
    row = await session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value


async def find_series_video(session: AsyncSession, series_id: int) -> dict | None:
    """系列的第一个视频内容：启用顶级帖按 (sort,id) 顺序，取正文中首个带 src 的视频块。"""
    posts = (
        await session.execute(
            select(BrandPost)
            .where(BrandPost.series_id == series_id, BrandPost.status == 1,
                   BrandPost.parent_id.is_(None))
            .order_by(BrandPost.sort, BrandPost.id)
        )
    ).scalars().all()
    for p in posts:
        for b in p.body or []:
            if isinstance(b, dict) and b.get("kind") == "video" and b.get("src"):
                return {"src": b["src"], "poster": b.get("poster") or "", "post_id": p.id}
    return None


async def resolve_home_video(session: AsyncSession) -> dict | None:
    """首页视频位：配置了系列且能解析出视频才返回，任何一环缺失都静默降级为 None。"""
    raw = await get_setting(session, HOME_VIDEO_KEY)
    if not raw.isdigit() or int(raw) == 0:
        return None
    s = await session.get(Series, int(raw))
    if s is None or s.status != 1:
        return None
    video = await find_series_video(session, s.id)
    if video is None:
        return None
    return {**video, "series_id": s.id, "series_name": s.name, "series_en": s.en}
