from sqlalchemy import BigInteger, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, BigIntPK


class Banner(Base):
    __tablename__ = "banner"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    position: Mapped[str] = mapped_column(String(32), default="home_hero", index=True)
    title: Mapped[str] = mapped_column(String(128))
    sub_title: Mapped[str] = mapped_column(String(128), default="")
    image: Mapped[str] = mapped_column(String(512), default="")
    link: Mapped[str] = mapped_column(String(256), default="")
    sort: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)
