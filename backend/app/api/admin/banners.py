from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.deps import DB
from app.errors import BizError
from app.models.cms import Banner
from app.models.series import Series
from app.schemas.admin import BannerIn, HomeVideoIn
from app.schemas.common import Resp
from app.services.cms import HOME_VIDEO_KEY, find_series_video, get_setting, set_setting

router = APIRouter()


async def _home_video_state(session) -> dict:
    """当前配置 + 按配置能解析出的视频（video=None 表示配置了但未生效/未配置）。"""
    raw = await get_setting(session, HOME_VIDEO_KEY)
    sid = int(raw) if raw.isdigit() else 0
    video = await find_series_video(session, sid) if sid else None
    return {"series_id": sid, "video": video}


@router.get("/home-video", response_model=Resp[dict])
async def get_home_video(session: DB):
    return Resp(data=await _home_video_state(session))


@router.put("/home-video", response_model=Resp[dict])
async def set_home_video(req: HomeVideoIn, session: DB):
    """配置首页视频位关联的系列；该系列的内容帖中必须已有视频块。series_id=0 清除。"""
    if req.series_id:
        s = await session.get(Series, req.series_id)
        if s is None:
            raise HTTPException(status_code=404, detail="系列不存在")
        if await find_series_video(session, req.series_id) is None:
            raise BizError("该系列还没有视频内容：请先在「品牌内容」里给关联此系列的帖子添加视频块")
    await set_setting(session, HOME_VIDEO_KEY, str(req.series_id or ""))
    await session.commit()
    return Resp(data=await _home_video_state(session))


def _row(b: Banner) -> dict:
    return {"id": b.id, "title": b.title, "sub_title": b.sub_title, "image": b.image,
            "link": b.link, "sort": b.sort, "status": b.status}


@router.get("/banners", response_model=Resp[list[dict]])
async def list_banners(session: DB):
    rows = (
        await session.execute(
            select(Banner).where(Banner.position == "home_hero").order_by(Banner.sort, Banner.id)
        )
    ).scalars().all()
    return Resp(data=[_row(b) for b in rows])


@router.post("/banners", response_model=Resp[dict])
async def create_banner(req: BannerIn, session: DB):
    b = Banner(position="home_hero", **req.model_dump())
    session.add(b)
    await session.commit()
    return Resp(data=_row(b))


@router.put("/banners/{banner_id}", response_model=Resp[dict])
async def update_banner(banner_id: int, req: BannerIn, session: DB):
    b = await session.get(Banner, banner_id)
    if b is None:
        raise HTTPException(status_code=404, detail="轮播不存在")
    for field, value in req.model_dump().items():
        setattr(b, field, value)
    await session.commit()
    return Resp(data=_row(b))


@router.delete("/banners/{banner_id}", response_model=Resp[None])
async def delete_banner(banner_id: int, session: DB):
    b = await session.get(Banner, banner_id)
    if b is None:
        raise HTTPException(status_code=404, detail="轮播不存在")
    await session.delete(b)
    await session.commit()
    return Resp()
