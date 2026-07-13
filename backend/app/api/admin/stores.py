from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.deps import DB
from app.models.store import Store
from app.schemas.admin import StoreIn
from app.schemas.common import Resp

router = APIRouter()


def _row(s: Store) -> dict:
    return {"id": s.id, "name": s.name, "short_name": s.short_name,
            "province": s.province, "city": s.city, "address": s.address,
            "tel": s.tel, "business_hours": s.business_hours,
            "images": s.images or [], "consultant_qr": s.consultant_qr,
            "lat": s.lat, "lng": s.lng, "sort": s.sort, "status": s.status}


@router.get("/stores", response_model=Resp[list[dict]])
async def list_stores(session: DB):
    rows = (await session.execute(select(Store).order_by(Store.sort, Store.id))).scalars().all()
    return Resp(data=[_row(s) for s in rows])


@router.post("/stores", response_model=Resp[dict])
async def create_store(req: StoreIn, session: DB):
    s = Store(**req.model_dump())
    session.add(s)
    await session.commit()
    return Resp(data=_row(s))


@router.put("/stores/{store_id}", response_model=Resp[dict])
async def update_store(store_id: int, req: StoreIn, session: DB):
    s = await session.get(Store, store_id)
    if s is None:
        raise HTTPException(status_code=404, detail="门店不存在")
    for field, value in req.model_dump().items():
        setattr(s, field, value)
    await session.commit()
    return Resp(data=_row(s))


@router.delete("/stores/{store_id}", response_model=Resp[None])
async def delete_store(store_id: int, session: DB):
    s = await session.get(Store, store_id)
    if s is None:
        raise HTTPException(status_code=404, detail="门店不存在")
    await session.delete(s)
    await session.commit()
    return Resp()
