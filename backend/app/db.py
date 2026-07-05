from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

if settings.database_url.startswith("sqlite"):
    # sqlite 仅用于本地/测试：NullPool 避免连接跨事件循环复用
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
else:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# MySQL 用 BIGINT 主键；SQLite 只对 INTEGER PRIMARY KEY 自增，需方言变体
from sqlalchemy import BigInteger, Integer  # noqa: E402

BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionFactory() as session:
        yield session


async def create_all() -> None:
    # MVP 阶段启动建表；schema 稳定后改为 alembic 迁移
    from app import models  # noqa: F401  确保模型已注册

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
