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


# 模型已经删掉、旧库仍留着的列。这些列当初只有 ORM 默认值，没有数据库默认值，
# 所以是 NOT NULL。ORM 不再写入它们时，MySQL 严格模式会让 INSERT 直接 500。
_RETIRED_COLUMNS = {
    "series": ("subtitle", "cover", "cover_tint"),
}


def _drop_retired_columns(conn) -> None:
    """删掉明确废弃的列。幂等：列已不在则跳过。仍在模型里的列不会删。"""
    import logging

    from sqlalchemy import inspect, text

    insp = inspect(conn)
    quote = conn.dialect.identifier_preparer.quote
    log = logging.getLogger(__name__)
    for table_name, cols in _RETIRED_COLUMNS.items():
        table = Base.metadata.tables.get(table_name)
        if table is None or not insp.has_table(table_name):
            continue
        live = {c.name for c in table.columns}
        existing = {c["name"] for c in insp.get_columns(table_name)}
        for col in cols:
            if col in live:
                raise RuntimeError(f"{table_name}.{col} 仍在模型里，不能当作废弃列删除")
            if col not in existing:
                continue
            conn.execute(text(f"ALTER TABLE {quote(table_name)} DROP COLUMN {quote(col)}"))
            log.warning("列迁移：%s 表删除废弃列 %s", table_name, col)


async def create_all() -> None:
    # MVP 阶段启动建表 + 轻量列迁移；schema 复杂化后改为 alembic
    from app import models  # noqa: F401  确保模型已注册

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_drop_retired_columns)
        await conn.run_sync(_add_missing_columns)
