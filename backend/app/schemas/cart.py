from pydantic import BaseModel, Field


class CartAdd(BaseModel):
    sku_id: int
    qty: int = Field(default=1, ge=1, le=999)


class CartPatch(BaseModel):
    qty: int = Field(ge=1, le=999)


class CartItemOut(BaseModel):
    id: int
    sku_id: int
    spu_id: int
    qty: int
    name: str
    en_model: str
    color_name: str
    color_hex: str
    size: str
    price: int
    stock: int
    image: str | None
