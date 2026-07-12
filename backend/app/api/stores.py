from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.deps import DB
from app.models.store import Store
from app.schemas.common import Resp

router = APIRouter()


def _row(s: Store) -> dict:
    return {
        "id": s.id, "name": s.name, "short_name": s.short_name,
        "province": s.province, "city": s.city, "address": s.address,
        "tel": s.tel, "business_hours": s.business_hours,
        "images": s.images or [], "consultant_qr": s.consultant_qr,
        "lat": s.lat, "lng": s.lng,
    }


@router.get("/stores", response_model=Resp[list[dict]])
async def list_stores(session: DB, province: str | None = None, city: str | None = None):
    stmt = select(Store).where(Store.status == 1)
    if province:
        stmt = stmt.where(Store.province == province)
    if city:
        stmt = stmt.where(Store.city == city)
    rows = (await session.execute(stmt.order_by(Store.sort, Store.id))).scalars().all()
    return Resp(data=[_row(s) for s in rows])


@router.get("/stores/regions", response_model=Resp[dict])
async def store_regions(session: DB):
    """门店省市，供附近门店下拉筛选。"""
    rows = (await session.execute(select(Store).where(Store.status == 1))).scalars().all()
    provs: list[str] = []
    cities: dict[str, list[str]] = {}
    for s in rows:
        if s.province and s.province not in provs:
            provs.append(s.province)
        cities.setdefault(s.province, [])
        if s.city and s.city not in cities[s.province]:
            cities[s.province].append(s.city)
    return Resp(data={"provinces": provs, "cities": cities})


@router.get("/stores/{store_id}", response_model=Resp[dict])
async def store_detail(store_id: int, session: DB):
    s = await session.get(Store, store_id)
    if s is None or s.status != 1:
        raise HTTPException(status_code=404, detail="门店不存在")
    return Resp(data=_row(s))
