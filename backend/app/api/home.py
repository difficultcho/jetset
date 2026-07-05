from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB
from app.models.catalog import Spu
from app.models.cms import Banner
from app.schemas.catalog import HomeOut
from app.schemas.common import Resp
from app.services.catalog import spu_to_list_item

router = APIRouter()


@router.get("/home", response_model=Resp[HomeOut])
async def home(session: DB):
    banners = (
        await session.execute(
            select(Banner)
            .where(Banner.position == "home_hero", Banner.status == 1)
            .order_by(Banner.sort)
        )
    ).scalars().all()

    spus = (
        await session.execute(
            select(Spu).where(Spu.status == 1).order_by(Spu.sort, Spu.id)
        )
    ).scalars().all()

    featured = next((s for s in spus if s.featured), None)
    return Resp(data=HomeOut(
        banners=[{"title": b.title, "sub_title": b.sub_title, "image": b.image} for b in banners],
        hot=[spu_to_list_item(s) for s in spus[:5]],
        featured=spu_to_list_item(featured) if featured else None,
        grid=[spu_to_list_item(s) for s in spus[3:]],
    ))
