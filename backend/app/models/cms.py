from sqlalchemy import JSON, BigInteger, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK


class Setting(Base):
    """全站键值配置：如首页视频位关联的系列 id。"""

    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(512), default="")


class Page(Base):
    """配置化页面（统一容器）：块序列自由编排，页面间用链接块互跳。
    固定挂载页 key=home（首页 tab）/brand（关于品牌 tab），其余为内容页（key 随机生成）。
    title 供别的页面用链接块指向它时展示。"""

    __tablename__ = "page"

    key: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(128), default="")
    blocks: Mapped[list] = mapped_column(JSON, default=list)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
