"""种子数据：将设计稿的 mock 商品迁移为 SPU/SKU。

用法: python -m app.seed  （幂等：已有商品则跳过）
"""

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionFactory, create_all, engine
from app.models.admin import AdminUser
from app.models.catalog import Category, Sku, Spu
from app.models.cms import Banner
from app.security import hash_password

CATEGORIES = ["冲锋衣", "包类", "短裤", "开衫", "登山鞋", "短袖", "滑雪"]

BANNERS = [
    {"title": "山海无界  陪伴无休", "sub_title": "EXPLORE WITHOUT LIMITS"},
    {"title": "专业户外  品质之选", "sub_title": "PROFESSIONAL OUTDOOR GEAR"},
    {"title": "瑞士阿尔卑斯  滑雪季", "sub_title": "SWISS ALPS SKI SEASON"},
]

# 价格单位为元（写库时 ×100 转分）
PRODUCTS = [
    {"name": "男款防水冲锋衣", "en": "HYDROVA-M 1.0", "price": 2399, "cat": "冲锋衣",
     "colors": [("林焰色（橙色）", "#E86A2B"), ("冰岚色（蓝色）", "#5B9BD4"), ("焦岩色（黑色）", "#2a2a2a")],
     "sizes": ["XS", "S", "M", "L", "XL", "XXL"], "badge": "热销",
     "desc": "三层压胶防水工艺，10000mm防水指数，全缝线热压处理，适合各种极限户外环境。"},
    {"name": "登山领队背包", "en": "LEADA 1.0", "price": 599, "cat": "包类",
     "colors": [("黑色", "#1a1a1a")], "sizes": ["均码"],
     "desc": "专业登山背包，40L大容量，多功能收纳分区，防水面料。"},
    {"name": "防水面料户外斜挎包", "en": "TRAILVA 1.0", "price": 280, "cat": "包类",
     "colors": [("薰衣草紫", "#B8A6D4"), ("黑色", "#2a2a2a")], "sizes": ["均码"], "featured": True,
     "desc": "随行斜挎包，考杜拉防水面料，可折叠收纳，轻便耐用。"},
    {"name": "男款无氟防泼水透气短裤", "en": "HYDROP-M 1.0", "price": 799, "cat": "短裤",
     "colors": [("夜玄色（黑色）", "#2a3a4a"), ("石灰色", "#9a9a9a")],
     "sizes": ["XS", "S", "M", "L", "XL", "XXL"],
     "desc": "无氟防泼水工艺，4向弹力面料，透气舒适，适合户外徒步。"},
    {"name": "阿尔卑斯双镜片滑雪镜", "en": "ALPINA 1.0", "price": 398, "cat": "滑雪",
     "colors": [("冰蓝色", "#4A90D9"), ("焦岩色（黑色）", "#2a2a2a")], "sizes": ["均码"],
     "desc": "瑞士工艺双层防雾镜片，抗UV400，宽视野框架，适合高山滑雪场景。"},
    {"name": "保暖防风滑雪手套", "en": "ZERMATT 1.0", "price": 328, "cat": "滑雪",
     "colors": [("雪岩白", "#e8e8e8"), ("焦岩色（黑色）", "#2a2a2a"), ("冰岚色（蓝色）", "#5B9BD4")],
     "sizes": ["S", "M", "L"],
     "desc": "源自瑞士雪山工艺，三层防风保暖结构，触屏指尖设计，零下30°仍保持灵活。"},
    {"name": "美利奴羊毛滑雪头巾", "en": "MATTERHORN 1.0", "price": 199, "cat": "滑雪",
     "colors": [("薰衣草紫", "#B8A6D4"), ("冰蓝色", "#5B9BD4")], "sizes": ["均码"],
     "desc": "瑞士美利奴羊毛混纺，透气保暖，多种佩戴方式，滑雪徒步皆宜。"},
    {"name": "滑雪护具背部护板", "en": "GLACIER 1.0", "price": 458, "cat": "滑雪",
     "colors": [("冰蓝色", "#6B9BD2"), ("灰色", "#888888")], "sizes": ["均码"],
     "desc": "高密度缓冲背板，符合欧洲雪具安全标准，专为高速滑降场景设计。"},
]

DEFAULT_STOCK = 100


async def seed_all(session: AsyncSession) -> bool:
    """已有商品则跳过，返回是否执行了写入。"""
    count = (await session.execute(select(func.count()).select_from(Spu))).scalar_one()
    if count > 0:
        return False

    cat_map: dict[str, Category] = {}
    for i, name in enumerate(CATEGORIES):
        cat = Category(name=name, sort=i)
        session.add(cat)
        cat_map[name] = cat

    for i, b in enumerate(BANNERS):
        session.add(Banner(position="home_hero", title=b["title"],
                           sub_title=b["sub_title"], sort=i))
    await session.flush()

    for i, p in enumerate(PRODUCTS):
        spu = Spu(
            category_id=cat_map[p["cat"]].id,
            name=p["name"], en_model=p["en"], brief=p["desc"],
            detail=p["desc"] + "专为户外爱好者设计，高性能防水面料，轻量化结构，满足登山、徒步、露营等多种场景需求。",
            badge=p.get("badge"), featured=p.get("featured", False),
            price=p["price"] * 100, sort=i,
        )
        session.add(spu)
        await session.flush()
        for ci, (cname, chex) in enumerate(p["colors"]):
            for size in p["sizes"]:
                session.add(Sku(
                    spu_id=spu.id, color_index=ci, color_name=cname, color_hex=chex,
                    size=size, price=p["price"] * 100, stock=DEFAULT_STOCK,
                ))
    return True


async def ensure_admin(session: AsyncSession) -> bool:
    """确保管理员账号存在（账号密码来自 ADMIN_USERNAME/ADMIN_PASSWORD 配置）。"""
    count = (await session.execute(select(func.count()).select_from(AdminUser))).scalar_one()
    if count > 0:
        return False
    session.add(AdminUser(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
    ))
    return True


async def main() -> None:
    await create_all()
    async with SessionFactory() as session:
        written = await seed_all(session)
        admin_created = await ensure_admin(session)
        await session.commit()
    # 退出前释放连接池，避免解释器关闭阶段报 "Event loop is closed"
    await engine.dispose()
    print("seeded" if written else "already seeded, skipped")
    if admin_created:
        print(f"admin created: {settings.admin_username}（密码来自 ADMIN_PASSWORD，生产务必修改）")


if __name__ == "__main__":
    asyncio.run(main())
