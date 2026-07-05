from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductListItem(BaseModel):
    id: int
    name: str
    en_model: str
    price: int  # 分
    badge: str | None
    image: str | None
    color_hexes: list[str]


class ColorOut(BaseModel):
    index: int
    name: str
    hex: str
    image: str | None


class SkuOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    color_index: int
    size: str
    price: int
    stock: int


class ProductDetail(BaseModel):
    id: int
    name: str
    en_model: str
    brief: str
    detail: str
    badge: str | None
    price: int
    colors: list[ColorOut]
    sizes: list[str]
    skus: list[SkuOut]


class HomeBanner(BaseModel):
    title: str
    sub_title: str
    image: str


class HomeOut(BaseModel):
    banners: list[HomeBanner]
    hot: list[ProductListItem]
    featured: ProductListItem | None
    grid: list[ProductListItem]
