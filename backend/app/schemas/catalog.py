from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class ProductListItem(BaseModel):
    id: int
    name: str
    sub: str
    en_model: str
    code: str
    series_en: str = ""
    price: int  # 分
    original_price: int | None = None
    badge: str | None
    has_video: bool = False
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
    sub: str
    en_model: str
    code: str
    brief: str
    detail: str
    bullets: list[str] = []
    badge: str | None
    has_video: bool = False
    price: int
    original_price: int | None = None
    series: dict | None = None
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
