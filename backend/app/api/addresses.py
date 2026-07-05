from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update

from app.deps import DB, CurrentUser
from app.models.address import Address
from app.schemas.address import AddressIn, AddressOut
from app.schemas.common import Resp

router = APIRouter()


async def _get_owned(session, user_id: int, addr_id: int) -> Address:
    addr = await session.get(Address, addr_id)
    if addr is None or addr.user_id != user_id:
        raise HTTPException(status_code=404, detail="地址不存在")
    return addr


async def _clear_default(session, user_id: int) -> None:
    await session.execute(
        update(Address).where(Address.user_id == user_id).values(is_default=False)
    )


@router.get("/addresses", response_model=Resp[list[AddressOut]])
async def list_addresses(user: CurrentUser, session: DB):
    rows = (
        await session.execute(
            select(Address)
            .where(Address.user_id == user.id)
            .order_by(Address.is_default.desc(), Address.created_at.desc(), Address.id.desc())
        )
    ).scalars().all()
    return Resp(data=[AddressOut.model_validate(a) for a in rows])


@router.post("/addresses", response_model=Resp[AddressOut])
async def create_address(req: AddressIn, user: CurrentUser, session: DB):
    # 与设计稿一致：新地址置为默认（插入列表顶部参与下单）
    await _clear_default(session, user.id)
    addr = Address(user_id=user.id, is_default=True, **req.model_dump())
    session.add(addr)
    await session.commit()
    return Resp(data=AddressOut.model_validate(addr))


@router.put("/addresses/{addr_id}", response_model=Resp[AddressOut])
async def update_address(addr_id: int, req: AddressIn, user: CurrentUser, session: DB):
    addr = await _get_owned(session, user.id, addr_id)
    for field, value in req.model_dump().items():
        setattr(addr, field, value)
    await session.commit()
    return Resp(data=AddressOut.model_validate(addr))


@router.put("/addresses/{addr_id}/default", response_model=Resp[AddressOut])
async def set_default(addr_id: int, user: CurrentUser, session: DB):
    addr = await _get_owned(session, user.id, addr_id)
    await _clear_default(session, user.id)
    addr.is_default = True
    await session.commit()
    return Resp(data=AddressOut.model_validate(addr))


@router.delete("/addresses/{addr_id}", response_model=Resp[None])
async def delete_address(addr_id: int, user: CurrentUser, session: DB):
    addr = await _get_owned(session, user.id, addr_id)
    await session.delete(addr)
    await session.commit()
    return Resp()
