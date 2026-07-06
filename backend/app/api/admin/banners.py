from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.deps import DB
from app.models.cms import Banner
from app.schemas.admin import BannerIn
from app.schemas.common import Resp

router = APIRouter()


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
