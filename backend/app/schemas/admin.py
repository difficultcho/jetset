from pydantic import BaseModel, Field


class AdminLoginReq(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class SkuIn(BaseModel):
    color_index: int = Field(ge=0)
    color_name: str = Field(min_length=1, max_length=64)
    color_hex: str = Field(default="#888888", max_length=16)
    size: str = Field(min_length=1, max_length=16)
    price: int = Field(ge=1)  # 分
    stock: int = Field(ge=0)
    status: int = Field(default=1, ge=0, le=1)


class ImageIn(BaseModel):
    color_index: int = Field(default=0, ge=0)
    url: str = Field(min_length=1, max_length=512)
    sort: int = 0


class ProductIn(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=128)
    en_model: str = Field(default="", max_length=64)
    brief: str = ""
    detail: str = ""
    badge: str | None = Field(default=None, max_length=16)
    featured: bool = False
    sort: int = 0
    status: int = Field(default=1, ge=0, le=1)
    skus: list[SkuIn] = Field(min_length=1)
    images: list[ImageIn] = []


class StatusReq(BaseModel):
    status: int = Field(ge=0, le=1)


class ShipReq(BaseModel):
    company: str = Field(min_length=1, max_length=32)
    tracking_no: str = Field(min_length=1, max_length=64)


class ReviewReq(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    note: str = Field(default="", max_length=256)


class BannerIn(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    sub_title: str = Field(default="", max_length=128)
    image: str = Field(default="", max_length=512)
    link: str = Field(default="", max_length=256)
    sort: int = 0
    status: int = Field(default=1, ge=0, le=1)
