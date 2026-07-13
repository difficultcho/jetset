from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.deps import DB
from app.models.catalog import Spu
from app.models.series import Series
from app.schemas.admin import SeriesIn
from app.schemas.common import Resp

router = APIRouter()


def _row(s: Series, product_count: int = 0) -> dict:
    return {"id": s.id, "name": s.name, "en": s.en, "subtitle": s.subtitle,
            "cover": s.cover, "cover_tint": s.cover_tint, "sort": s.sort,
            "status": s.status, "product_count": product_count}


@router.get("/series", response_model=Resp[list[dict]])
async def list_series(session: DB):
    rows = (await session.execute(select(Series).order_by(Series.sort, Series.id))).scalars().all()
    counts = dict(
        (await session.execute(select(Spu.series_id, func.count()).group_by(Spu.series_id))).all()
    )
    return Resp(data=[_row(s, counts.get(s.id, 0)) for s in rows])


@router.post("/series", response_model=Resp[dict])
async def create_series(req: SeriesIn, session: DB):
    s = Series(**req.model_dump())
    session.add(s)
    await session.commit()
    return Resp(data=_row(s))


@router.put("/series/{series_id}", response_model=Resp[dict])
async def update_series(series_id: int, req: SeriesIn, session: DB):
    s = await session.get(Series, series_id)
    if s is None:
        raise HTTPException(status_code=404, detail="系列不存在")
    for field, value in req.model_dump().items():
        setattr(s, field, value)
    await session.commit()
    return Resp(data=_row(s))


@router.delete("/series/{series_id}", response_model=Resp[None])
async def delete_series(series_id: int, session: DB):
    s = await session.get(Series, series_id)
    if s is None:
        raise HTTPException(status_code=404, detail="系列不存在")
    used = (
        await session.execute(select(func.count()).where(Spu.series_id == series_id))
    ).scalar_one()
    if used:
        raise HTTPException(status_code=400, detail=f"仍有 {used} 个商品归属该系列，请先移出")
    await session.delete(s)
    await session.commit()
    return Resp()
