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
    category_id: int                       # 二级（叶子）品类
    series_id: int | None = None           # 归属系列
    name: str = Field(min_length=1, max_length=128)
    sub: str = Field(default="", max_length=128)       # 短名（卡片/走马灯）
    en_model: str = Field(default="", max_length=64)   # 兼容保留
    code: str = Field(default="", max_length=64)       # 款号
    brief: str = ""
    detail: str = ""
    bullets: list[str] = []                # 产品细节条目
    badge: str | None = Field(default=None, max_length=16)
    featured: bool = False
    has_video: bool = False
    original_price: int | None = Field(default=None, ge=1)  # 划线原价（分）
    sort: int = 0
    status: int = Field(default=1, ge=0, le=1)
    skus: list[SkuIn] = Field(min_length=1)
    images: list[ImageIn] = []


class SeriesIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    en: str = Field(default="", max_length=64)
    subtitle: str = Field(default="", max_length=128)
    cover: str = Field(default="", max_length=512)
    cover_tint: str = Field(default="#e8dcc8", max_length=16)
    sort: int = 0
    status: int = Field(default=1, ge=0, le=1)


class StoreIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    short_name: str = Field(default="", max_length=64)
    province: str = Field(default="", max_length=32)
    city: str = Field(default="", max_length=32)
    address: str = Field(default="", max_length=256)
    tel: str = Field(default="", max_length=32)
    business_hours: str = Field(default="", max_length=128)
    images: list[str] = []
    consultant_qr: str = Field(default="", max_length=512)
    lat: float | None = None
    lng: float | None = None
    sort: int = 0
    status: int = Field(default=1, ge=0, le=1)


class BrandPostIn(BaseModel):
    type: str = Field(pattern="^(project|moment|campaign|story)$")
    title: str = Field(min_length=1, max_length=128)
    subtitle: str = Field(default="", max_length=256)
    cover: str = Field(default="", max_length=512)
    cover_tint: str = Field(default="#e6ddce", max_length=16)
    body: list[dict] = []   # [{kind: image|text|quote, ...}]
    link: str = Field(default="", max_length=256)
    sort: int = 0
    status: int = Field(default=1, ge=0, le=1)


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
