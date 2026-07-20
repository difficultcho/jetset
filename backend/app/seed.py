"""AURELLE 种子数据：品类树 + 系列 + 商品(SPU/SKU) + 门店 + 品牌内容。

用法: python -m app.seed （幂等：已有商品则跳过商品部分）
"""

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import SessionFactory, create_all, engine
from app.models.admin import AdminUser
from app.models.catalog import Category, Sku, Spu
from app.models.cms import Page
from app.models.series import Series
from app.models.store import Store
from app.security import hash_password

# 品类树：一级 → 二级
CATEGORY_TREE = [
    ("连衣裙", "DRESSES", ["长款", "中长款", "短款"]),
    ("上衣", "TOPS", ["衬衫", "斗篷"]),
    ("鞋履", "SHOES", ["高跟鞋", "穆勒鞋", "凉鞋"]),
    ("包袋", "BAGS", ["手拿包", "单肩包"]),
    ("珠宝", "JEWELLERY", ["项链"]),
    ("配饰", "ACCESSORIES", []),
    ("童装", "KIDS", []),
]

# 系列（en, name/subtitle, tint）
SERIES = [
    ("HIGH SUMMER", "2026夏日胶囊系列", "现已于精品店及线上同步发售", "#e9dfce"),
    ("CRUISE 2027", "度假成衣秀场", "探索度假系列的松弛美学", "#dfe5e9"),
    ("NEW ARRIVALS", "新品上新", "本季最新到店单品", "#e6ddce"),
]

DRESS_SIZES = ["0", "1", "2", "3"]
SHOE_SIZES = ["36", "37", "38", "39", "40"]
ONE_SIZE = ["均码"]

# 商品：name, sub, code, 价元, sale元(可空), 二级品类, 系列en, 颜色名, 色值, sizes, video, bullets
PRODUCTS = [
    ("SOLEIL 挂脖牛仔连衣裙", "挂脖牛仔连衣裙", "AU433DSS266", 9650, None, "中长款", "HIGH SUMMER",
     "蓝色", "#4a5d7e", DRESS_SIZES, True,
     "这款蓝色 SOLEIL 挂脖连衣裙以轻盈牛仔面料制成，立领挂脖设计，后领处系带，腰间垂褶层叠，裙身紧密缩褶，裙摆呈高低错落的不对称剪裁，复古而优雅。",
     ["棉质轻牛仔面料", "无袖设计，中长款裙长剪裁", "领口挂脖系带", "腰部褶饰，侧边垂褶式系带", "低露背款式", "左侧隐形拉链", "裙摆高低错落不对称剪裁"]),
    ("SOLEIL 领部系带短款连衣裙", "领部系带短款连衣裙", "AU433DSS270", 12700, None, "短款", "HIGH SUMMER",
     "拼色印花", "#b5854f", DRESS_SIZES, False,
     "轻薄绢丝面料，领部系带蝴蝶结设计，宽松落肩袖，不规则手帕式裙摆。",
     ["绢丝雪纺面料", "领部系带蝴蝶结", "宽松落肩袖型", "不规则手帕裙摆"]),
    ("SOLEIL 流苏细节长款连衣裙", "流苏细节长款连衣裙", "AU433DSS281", 12100, None, "长款", "HIGH SUMMER",
     "雾蓝", "#8794c9", DRESS_SIZES, False,
     "层叠式荷叶边裙身，肩部系带缀流苏坠饰，垂坠感极佳的长款剪裁。",
     ["层叠荷叶边裙身", "肩部系带流苏坠饰", "长款垂坠剪裁"]),
    ("SOLEIL 丝巾拼接设计连衣裙", "丝巾拼接设计连衣裙", "AU433DSS295", 21750, None, "长款", "HIGH SUMMER",
     "拼色印花", "#c08a76", DRESS_SIZES, False,
     "多幅印花丝巾拼接而成，领部系带，长袖阔摆，裙摆呈自然垂角。",
     ["真丝斜纹面料", "多幅印花拼接", "领部系带设计", "不对称垂角裙摆"]),
    ("SOLEIL 领部系带绢丝上衣", "领部系带绢丝上衣", "AU433TOP110", 8800, None, "衬衫", "HIGH SUMMER",
     "霞粉", "#d9a8a4", DRESS_SIZES, False,
     "轻盈绢丝面料，泡泡袖廓形，领口抽褶系带。",
     ["绢丝雪纺面料", "泡泡袖廓形", "领口抽褶系带"]),
    ("SOLEIL 流苏细节斗篷", "流苏细节斗篷", "AU433CAP021", 15500, None, "斗篷", "HIGH SUMMER",
     "赤陶", "#b96a4d", DRESS_SIZES, False,
     "印花绢丝斗篷，边缘缀以垂坠流苏，领口系带。",
     ["印花绢丝面料", "边缘垂坠流苏", "领口系带"]),
    ("CALLA 6.5厘米高跟穆勒鞋", "6.5厘米高跟穆勒鞋", "AU433SHO065", 5350, None, "穆勒鞋", "HIGH SUMMER",
     "米白", "#e6e0d4", SHOE_SIZES, False,
     "编织纹理粗跟，金属圆扣装饰，一字带穆勒设计。",
     ["编织纹理粗跟 6.5cm", "金属圆扣装饰", "小牛皮鞋面"]),
    ("CALLA 10.5厘米高跟防水台凉鞋", "10.5厘米防水台凉鞋", "AU433SHO105", 5700, None, "凉鞋", "CRUISE 2027",
     "浅驼", "#d4b98c", SHOE_SIZES, False,
     "编织包覆防水台与鞋跟，踝部搭扣固定。",
     ["防水台高度 3cm", "编织包覆鞋跟 10.5cm", "踝部搭扣"]),
    ("铆钉细节花朵造型8.5厘米高跟凉鞋", "花朵造型高跟凉鞋", "AU433SHO085", 7350, 3675, "凉鞋", "CRUISE 2027",
     "棕", "#9a5b3c", SHOE_SIZES, False,
     "立体花朵装饰缀铆钉细节，纤细踝带设计。",
     ["立体花朵装饰", "铆钉细节", "踝带固定 8.5cm"]),
    ("CALLA 6.5厘米高跟穆勒鞋 棕", "6.5厘米高跟穆勒鞋", "AU433SHO066", 5350, None, "穆勒鞋", "HIGH SUMMER",
     "焦糖棕", "#8e5a34", SHOE_SIZES, False,
     "编织纹理粗跟，金属圆扣装饰，一字带穆勒设计。",
     ["编织纹理粗跟 6.5cm", "金属圆扣装饰", "小牛皮鞋面"]),
    ("RIVA 编织手拿包", "编织手拿包", "AU433BAG031", 6900, None, "手拿包", "HIGH SUMMER",
     "原麻", "#cbb28c", ONE_SIZE, False,
     "手工编织酒椰纤维，褶浪造型包身，附可拆卸长链。",
     ["酒椰纤维手工编织", "褶浪造型包身", "可拆卸长链"]),
    ("RIVA 皮革单肩包", "皮革单肩包", "AU433BAG045", 8900, None, "单肩包", "NEW ARRIVALS",
     "黑", "#2e2c2a", ONE_SIZE, False,
     "柔软小牛皮抽褶包身，磁吸开合。",
     ["柔软小牛皮", "抽褶包身", "磁吸开合"]),
    ("SOLEIL 天然石坠饰项链", "天然石坠饰项链", "AU433JWL012", 3200, None, "项链", "HIGH SUMMER",
     "金", "#c9a25a", ONE_SIZE, False,
     "皮革绳链缀天然石坠饰，可调节长度。",
     ["天然石坠饰", "皮革绳链", "长度可调"]),
]

STORES = [
    {"name": "北京三里屯精品店", "short_name": "北京三里屯", "province": "北京市", "city": "北京市",
     "address": "北京市朝阳区三里屯路南区，L1层S6-18，L2层S6-25商铺", "tel": "010-8860 3618",
     "business_hours": "周日至周四 10:00-22:00，周五至周六 10:00-23:00", "lat": 39.9367, "lng": 116.4550},
    {"name": "上海南京西路精品店", "short_name": "上海南京西路", "province": "上海市", "city": "上海市",
     "address": "上海市静安区南京西路1266号，L1层112商铺", "tel": "021-6288 1866",
     "business_hours": "周一至周日 10:00-22:00", "lat": 31.2277, "lng": 121.4610},
    {"name": "成都春熙路精品店", "short_name": "成都春熙路", "province": "四川省", "city": "成都市",
     "address": "成都市锦江区中纱帽街8号，M68商铺", "tel": "028-6511 8898",
     "business_hours": "周一至周日 10:00-22:00", "lat": 30.6520, "lng": 104.0817},
]

DEFAULT_STOCK = 50


async def seed_catalog(session: AsyncSession) -> bool:
    if (await session.execute(select(func.count()).select_from(Spu))).scalar_one() > 0:
        return False

    # 品类树
    leaf_by_name: dict[str, Category] = {}
    for si, (cn, en, subs) in enumerate(CATEGORY_TREE):
        top = Category(name=cn, en=en, sort=si)
        session.add(top)
        await session.flush()
        if not subs:
            leaf_by_name[cn] = top  # 无二级时商品直接挂一级
        for sj, sub in enumerate(subs):
            leaf = Category(name=sub, en="", parent_id=top.id, sort=sj)
            session.add(leaf)
            leaf_by_name[sub] = leaf

    # 系列
    series_by_en: dict[str, Series] = {}
    for si, (en, name, subtitle, tint) in enumerate(SERIES):
        s = Series(name=name, en=en, subtitle=subtitle, cover_tint=tint, sort=si)
        session.add(s)
        series_by_en[en] = s
    await session.flush()

    # 商品
    for i, p in enumerate(PRODUCTS):
        (name, sub, code, price_y, sale_y, cat_name, series_en,
         color_name, color_hex, sizes, video, desc, bullets) = p
        price = (sale_y if sale_y else price_y) * 100
        original = price_y * 100 if sale_y else None
        spu = Spu(
            category_id=leaf_by_name[cat_name].id,
            series_id=series_by_en[series_en].id,
            name=name, sub=sub, en_model=code, code=code,
            brief=desc, detail=desc + "以轻盈面料与考究工艺呈现松弛而优雅的当代廓形，适合度假与日常穿着。",
            bullets=bullets, has_video=video,
            price=price, original_price=original,
            badge=("SALE" if sale_y else None), featured=(i < 3), sort=i,
        )
        session.add(spu)
        await session.flush()
        for size in sizes:
            session.add(Sku(
                spu_id=spu.id, color_index=0, color_name=color_name, color_hex=color_hex,
                size=size, price=price, stock=DEFAULT_STOCK,
            ))
    return True


async def seed_stores(session: AsyncSession) -> None:
    if (await session.execute(select(func.count()).select_from(Store))).scalar_one() > 0:
        return
    for i, s in enumerate(STORES):
        session.add(Store(sort=i, images=[], **s))


async def seed_pages(session: AsyncSession) -> None:
    """配置化页面种子：首页 / 关于品牌两个 tab 挂载页 + 一个示例内容页（品牌故事）。
    页面间用链接块互跳；真实排版由用户在管理端「页面管理」搭建。"""
    if (await session.execute(select(func.count()).select_from(Page))).scalar_one() > 0:
        return
    # 内容页：品牌故事（被首页 / 关于品牌页链接引用）
    session.add(Page(key="story", title="品牌故事", cover_tint="#e6ddce", sort=1, blocks=[
        {"kind": "text", "preset": "eyebrow", "text": "THE STORY", "align": "center"},
        {"kind": "text", "preset": "quote", "text": "为山巅与海岸而生。", "align": "center"},
        {"kind": "text", "preset": "para",
         "text": "JET SET 诞生于对极致户外体验的向往，以轻盈的科技面料与克制的设计语言，"
                 "陪伴每一次向雪线与浪尖的出发。", "align": "left"},
    ]))
    # 首页 tab
    session.add(Page(key="home", title="首页", blocks=[
        {"kind": "carousel", "source": "featured", "count": 6},
        {"kind": "linkrow",
         "left": {"text": "探索品牌故事", "link": {"kind": "page", "key": "story"}},
         "right": {"text": "全部商品", "link": {"kind": "list"}}},
    ]))
    # 关于品牌 tab
    session.add(Page(key="brand", title="关于品牌", blocks=[
        {"kind": "text", "preset": "eyebrow", "text": "THE STORY", "align": "center"},
        {"kind": "linkrow",
         "left": {"text": "品牌故事", "link": {"kind": "page", "key": "story"}},
         "right": {"text": "全部商品", "link": {"kind": "list"}}},
        {"kind": "carousel", "source": "featured", "count": 6},
    ]))


async def ensure_admin(session: AsyncSession) -> bool:
    if (await session.execute(select(func.count()).select_from(AdminUser))).scalar_one() > 0:
        return False
    session.add(AdminUser(username=settings.admin_username,
                          password_hash=hash_password(settings.admin_password)))
    return True


async def seed_all(session: AsyncSession) -> bool:
    written = await seed_catalog(session)
    await seed_stores(session)
    await seed_pages(session)
    return written


async def main() -> None:
    await create_all()
    async with SessionFactory() as session:
        written = await seed_all(session)
        admin_created = await ensure_admin(session)
        await session.commit()
    await engine.dispose()
    print("seeded AURELLE" if written else "catalog already seeded, skipped")
    if admin_created:
        print(f"admin created: {settings.admin_username}")


if __name__ == "__main__":
    asyncio.run(main())
