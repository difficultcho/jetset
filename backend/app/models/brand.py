from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK
from app.utils import utcnow


class BrandPost(Base):
    """品牌内容（统一模型）：A.PROJECTS / A.MOMENTS / 广告大片 / 品牌故事。
    type=project 仅用卡片字段；campaign/moment/story 用 body 图文块渲染详情页。"""

    __tablename__ = "brand_post"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(16), index=True)  # project|moment|campaign|story
    title: Mapped[str] = mapped_column(String(128))
    subtitle: Mapped[str] = mapped_column(String(256), default="")
    cover: Mapped[str] = mapped_column(String(512), default="")
    cover_tint: Mapped[str] = mapped_column(String(16), default="#e6ddce")
    # 图文块 [{ "kind": "image"|"text", "value": "...", "tint": "#..", "ph": ".." }]
    body: Mapped[list] = mapped_column(JSON, default=list)
    link: Mapped[str] = mapped_column(String(256), default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
