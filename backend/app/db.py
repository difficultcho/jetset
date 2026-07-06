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


def _add_missing_columns(conn) -> None:
    """轻量列迁移：模型新增的列自动 ALTER 补齐（幂等，只加列、不改不删）。

    注意：新增 NOT NULL 列必须带 server_default，否则旧表 ALTER 会失败。
    """
    import logging

    from sqlalchemy import inspect, text
    from sqlalchemy.schema import CreateColumn

    insp = inspect(conn)
    for table in Base.metadata.tables.values():
        if not insp.has_table(table.name):
            continue
        existing = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing:
                continue
            ddl = CreateColumn(col).compile(dialect=conn.dialect)
            conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {ddl}"))
            logging.getLogger(__name__).warning("列迁移：%s 表新增列 %s", table.name, col.name)


async def create_all() -> None:
    # MVP 阶段启动建表 + 轻量列迁移；schema 复杂化后改为 alembic
    from app import models  # noqa: F401  确保模型已注册

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)
