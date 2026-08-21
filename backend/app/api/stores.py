from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.deps import DB
from app.models.store import Store
from app.schemas.common import Resp

router = APIRouter()


def _row(s: Store) -> dict:
    return {
        "id": s.id, "name": s.name, "short_name": s.short_name,
        "country": s.country, "province": s.province, "city": s.city,
        "address": s.address, "tel": s.tel, "business_hours": s.business_hours,
        "images": s.images or [], "consultant_qr": s.consultant_qr,
        "lat": s.lat, "lng": s.lng,
    }


@router.get("/stores", response_model=Resp[list[dict]])
async def list_stores(session: DB, country: str | None = None, city: str | None = None):
    stmt = select(Store).where(Store.status == 1)
    if country:
        stmt = stmt.where(Store.country == country)
    if city:
        stmt = stmt.where(Store.city == city)
    rows = (await session.execute(stmt.order_by(Store.sort, Store.id))).scalars().all()
    return Resp(data=[_row(s) for s in rows])


@router.get("/stores/regions", response_model=Resp[dict])
async def store_regions(session: DB):
    """门店的国家/地区与城市，供门店页两级下拉筛选。

    顺序沿用门店自身的 sort——运营把上海店 sort 调到最小，中国就排在最前，
    不需要在代码里写死任何国家名。
    """
    rows = (
        await session.execute(
            select(Store).where(Store.status == 1).order_by(Store.sort, Store.id)
        )
    ).scalars().all()
    countries: list[str] = []
    cities: dict[str, list[str]] = {}
    for s in rows:
        if not s.country:
            continue
        if s.country not in countries:
            countries.append(s.country)
            cities[s.country] = []
        if s.city and s.city not in cities[s.country]:
            cities[s.country].append(s.city)
    return Resp(data={"countries": countries, "cities": cities})


@router.get("/stores/{store_id}", response_model=Resp[dict])
async def store_detail(store_id: int, session: DB):
    s = await session.get(Store, store_id)
    if s is None or s.status != 1:
        raise HTTPException(status_code=404, detail="门店不存在")
    return Resp(data=_row(s))
