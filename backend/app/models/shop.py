from sqlalchemy import JSON, BigInteger, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK


class ShopMenu(Base):
    """商城左菜单项 + 该项选中时右侧上部的图片跳链。

    两组菜单项，来源不同：
      kind='series'   上部自定义项，完全由本表定义（增删排序都在这里）
      kind='category' 下部一级类目，由品类树派生；本表只为其附加图片跳链，
                      名称/排序/上下架仍以「品类管理」为准，避免两处配置打架
    """

    __tablename__ = "shop_menu"
    __table_args__ = (UniqueConstraint("kind", "ref_id", name="uq_shop_menu_ref"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), default="series")
    ref_id: Mapped[int] = mapped_column(BigInteger, index=True)  # series.id 或 category.id（一级）
    title: Mapped[str] = mapped_column(String(64), default="", server_default="")  # 空=取实体名
    en: Mapped[str] = mapped_column(String(64), default="", server_default="")
    banners: Mapped[list] = mapped_column(JSON, default=list)  # [{img, link}] 右侧上部图片跳链
    sort: Mapped[int] = mapped_column(Integer, default=0)      # 仅 kind='series' 生效
    status: Mapped[int] = mapped_column(SmallInteger, default=1)  # 仅 kind='series' 生效
