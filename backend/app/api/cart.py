from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.deps import DB, CurrentUser
from app.models.cart import CartItem
from app.models.catalog import Sku
from app.schemas.cart import CartAdd, CartItemOut, CartPatch
from app.schemas.common import Resp
from app.services.orders import _color_image

router = APIRouter()


async def _cart_out(session, user_id: int) -> list[CartItemOut]:
    rows = (
        await session.execute(
            select(CartItem, Sku)
            .join(Sku, CartItem.sku_id == Sku.id)
            .options(selectinload(Sku.spu))
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.desc(), CartItem.id.desc())
        )
    ).all()
    return [
        CartItemOut(
            id=ci.id, sku_id=sku.id, spu_id=sku.spu_id, qty=ci.qty,
            name=sku.spu.name, en_model=sku.spu.code or sku.spu.en_model,
            color_name=sku.color_name, color_hex=sku.color_hex, size=sku.size,
            price=sku.price, stock=sku.stock, image=_color_image(sku) or None,
        )
        for ci, sku in rows
    ]


@router.get("/cart", response_model=Resp[list[CartItemOut]])
async def get_cart(user: CurrentUser, session: DB):
    return Resp(data=await _cart_out(session, user.id))


@router.post("/cart/items", response_model=Resp[list[CartItemOut]])
async def add_item(req: CartAdd, user: CurrentUser, session: DB):
    sku = await session.get(Sku, req.sku_id)
    if sku is None or sku.status != 1:
        raise HTTPException(status_code=404, detail="商品规格不存在")
    existing = (
        await session.execute(
            select(CartItem).where(CartItem.user_id == user.id, CartItem.sku_id == req.sku_id)
        )
    ).scalar_one_or_none()
    if existing:
        existing.qty += req.qty  # 同规格合并数量
    else:
        session.add(CartItem(user_id=user.id, sku_id=req.sku_id, qty=req.qty))
    await session.commit()
    return Resp(data=await _cart_out(session, user.id))


@router.patch("/cart/items/{item_id}", response_model=Resp[list[CartItemOut]])
async def patch_item(item_id: int, req: CartPatch, user: CurrentUser, session: DB):
    item = await session.get(CartItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    item.qty = req.qty
    await session.commit()
    return Resp(data=await _cart_out(session, user.id))


@router.delete("/cart/items/{item_id}", response_model=Resp[list[CartItemOut]])
async def delete_item(item_id: int, user: CurrentUser, session: DB):
    item = await session.get(CartItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="购物车项不存在")
    await session.delete(item)
    await session.commit()
    return Resp(data=await _cart_out(session, user.id))
