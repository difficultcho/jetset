from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK
from app.utils import utcnow


class BrandPost(Base):
    """品牌内容（统一容器）：story 品牌故事 / campaign 广告大片（推新系列）/
    project 活动项目（两级：项目→子项目）/ moment 活动瞬间集。

    - series_id：关联系列 → 详情页尾部渲染该系列单品导购条
    - parent_id：活动子项目挂在父项目下（仅 project 用，两级）
    """

    __tablename__ = "brand_post"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(16), index=True)  # project|moment|campaign|story
    title: Mapped[str] = mapped_column(String(128))
    subtitle: Mapped[str] = mapped_column(String(256), default="")
    cover: Mapped[str] = mapped_column(String(512), default="")
    cover_tint: Mapped[str] = mapped_column(String(16), default="#e6ddce")
    # 图文块 [{kind: image|text|quote|video, value/img/src/poster, tint, ph, ratio, inset}]
    body: Mapped[list] = mapped_column(JSON, default=list)
    series_id: Mapped[int | None] = mapped_column(ForeignKey("series.id"), default=None, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("brand_post.id"), default=None, index=True)
    link: Mapped[str] = mapped_column(String(256), default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
