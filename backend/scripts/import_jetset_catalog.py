"""JET SET 真实商品建档：品类树 + STARS 系列 + 9 款商品（挂真图）+ 下架 AURELLE 演示数据。

用法（在 backend/ 下，需先部署含品类管理 API 的新版后端）：
    ADMIN_PASSWORD=<密码> .venv/bin/python scripts/import_jetset_catalog.py <图片目录>

图片目录 = 已按商品命名的素材目录（star-pants-black.jpg 等 13 张）。
价格均为占位价（参考官网奢侈滑雪装档位取整），后台商品编辑里随时改。
可重复执行：品类按（名称,父级）、系列按 en、商品按款号去重；下架操作幂等。
"""
import mimetypes
import os
import sys
from pathlib import Path

import httpx

BASE = os.environ.get("JETSET_BASE", "https://bce.kkmsee.com/jetset")
TIMEOUT = httpx.Timeout(300, connect=15)

# ---- 品类树（一级 → 二级）----
CATEGORY_TREE = [
    ("滑雪服", "SKI", ["滑雪裤", "滑雪夹克", "羽绒服", "滑雪配饰"]),
    ("成衣", "APRES-SKI", ["长裤"]),
]
CHILD_EN = {"滑雪裤": "SKI PANTS", "滑雪夹克": "SKI JACKETS", "羽绒服": "DOWN",
            "滑雪配饰": "ACCESSORIES", "长裤": "TROUSERS"}

SERIES_STARS = {"name": "星星系列", "en": "STARS", "subtitle": "JET SET 标志性星标",
                "cover_tint": "#dfe5e9", "sort": 0, "status": 1}

SIZES = ["XS", "S", "M", "L"]

# ---- 商品（价格单位：分，占位价）----
PRODUCTS = [
    {
        "name": "星标喇叭滑雪裤", "code": "2521220037", "cat": "滑雪裤", "series": True,
        "brief": "标志性星星贴花软壳滑雪裤，高腰束带，喇叭裤型。",
        "bullets": ["标志性星星侧饰", "高腰金属扣束带", "裤脚拉链开衩", "四向弹力软壳面料"],
        "price": 788000, "featured": True,
        "colors": [("黑色", "#141414", ["star-pants-black.jpg"]),
                   ("苔绿", "#4e6b3d", ["star-pants-green-front.jpg", "star-pants-green-side.jpg"])],
    },
    {
        "name": "棋盘星标滑雪裤", "code": "25211100130096", "cat": "滑雪裤", "series": True,
        "brief": "黑白棋盘格织带缀金星侧条，象牙白修身滑雪裤。",
        "bullets": ["棋盘格织带 · 金星贴花", "高腰束带", "裤脚拉链开衩"],
        "price": 828000, "featured": False,
        "colors": [("象牙白", "#f0ede4",
                    ["checker-pants-front.jpg", "checker-pants-side.jpg", "checker-pants-alt.jpg"])],
    },
    {
        "name": "拼色绗缝滑雪夹克", "code": "25212100168200", "cat": "滑雪夹克", "series": True,
        "brief": "黑白拼色绗缝滑雪夹克，立领修身，搭配星标滑雪裤。",
        "bullets": ["黑白拼色绗缝", "立领防风", "腋下透气拉链"],
        "price": 1280000, "featured": True,
        "colors": [("黑白", "#1a1a1a", ["quilt-jacket-look.jpg"])],
    },
    {
        "name": "机能滑雪夹克", "code": "26335102025101", "cat": "滑雪夹克", "series": False,
        "brief": "三层复合机能面料，防水透气，可拆卸毛饰连帽。",
        "bullets": ["20K 防水透气", "可拆卸毛饰兜帽", "雪裙 · 腋下透气拉链", "荧光拉链细节"],
        "price": 1580000, "featured": False,
        "colors": [("淡紫", "#d9d5e4", ["shell-jacket-lilac.jpg"])],
    },
    {
        "name": "渐变绗缝短夹克", "code": "26335102018227", "cat": "滑雪夹克", "series": False,
        "brief": "军绿古铜渐变绗缝短夹克，罗纹立领，轻量保暖。",
        "bullets": ["渐变光泽面料", "竖向绗缝", "罗纹立领"],
        "price": 988000, "featured": False,
        "colors": [("军绿", "#5a5b3a", ["bomber-olive.jpg"])],
    },
    {
        "name": "连帽羽绒夹克", "code": "JS2520DWN01", "cat": "羽绒服", "series": False,
        "brief": "廓形连帽羽绒夹克，V 型绗缝，酒红色调。",
        "bullets": ["90 绒鹅绒填充", "廓形落肩", "V 型绗缝"],
        "price": 1380000, "featured": False,
        "colors": [("酒红", "#4e2430", ["down-burgundy.jpg"])],
    },
    {
        "name": "缎面羽绒夹克", "code": "JS2520DWN02", "cat": "羽绒服", "series": False,
        "brief": "银色缎面短款羽绒夹克，高立领，光泽廓形。",
        "bullets": ["缎面光泽", "高立领", "短款廓形"],
        "price": 1480000, "featured": False,
        "colors": [("银灰", "#c9ccc9", ["down-silver.jpg"])],
    },
    {
        "name": "蛇纹阔腿长裤", "code": "26336205197071", "cat": "长裤", "series": False,
        "brief": "蛇纹印花阔腿长裤，压褶垂坠，山下时光之选。",
        "bullets": ["蛇纹印花", "压褶阔腿", "徽章细节"],
        "price": 588000, "featured": False,
        "colors": [("卡其", "#8b7f63", ["snake-pants.jpg"])],
    },
    {
        "name": "雪地连指手套", "code": "JS2520GLV01", "cat": "滑雪配饰", "series": False,
        "brief": "羊毛混纺连指手套，蝴蝶印花衬里，金属搭扣。",
        "bullets": ["羊毛混纺", "蝴蝶印花衬里", "金属搭扣"],
        "price": 288000, "featured": False, "sizes": ["均码"],
        "colors": [("黑色", "#141414", ["gloves-black.jpg"])],
    },
]

AURELLE_TOPS = ["连衣裙", "上衣", "鞋履", "包袋", "珠宝", "配饰", "童装"]
AURELLE_SERIES_EN = ["HIGH SUMMER", "CRUISE 2027", "NEW ARRIVALS"]


def unwrap(resp: httpx.Response) -> dict | list | None:
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(f"{resp.request.url}: {body.get('message')}")
    return body.get("data")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    asset_dir = Path(sys.argv[1])

    client = httpx.Client(base_url=BASE, timeout=TIMEOUT, trust_env=False)
    login = client.post("/api/admin/auth/login", json={
        "username": os.environ.get("ADMIN_USER", "admin"),
        "password": os.environ.get("ADMIN_PASSWORD", "jetset-admin"),
    })
    if login.status_code == 401:
        sys.exit("✗ 管理员账号/密码错误：请带 ADMIN_PASSWORD=<你的密码> 重新运行")
    client.headers["Authorization"] = "Bearer " + unwrap(login)["token"]
    print(f"✓ 登录成功：{BASE}")

    # 1) 品类树（幂等）
    cats = unwrap(client.get("/api/admin/categories"))
    by_key = {(c["name"], c["parent_id"]): c for c in cats}

    def ensure_cat(name: str, en: str, parent_id: int | None, sort: int) -> dict:
        row = by_key.get((name, parent_id))
        if row:
            return row
        row = unwrap(client.post("/api/admin/categories", json={
            "name": name, "en": en, "parent_id": parent_id, "sort": sort}))
        by_key[(name, parent_id)] = row
        print(f"✓ 品类「{name}」({'二级' if parent_id else '一级'})")
        return row

    leaf_id: dict[str, int] = {}
    for i, (top_name, top_en, children) in enumerate(CATEGORY_TREE):
        top = ensure_cat(top_name, top_en, None, i)
        for j, child in enumerate(children):
            leaf_id[child] = ensure_cat(child, CHILD_EN[child], top["id"], j)["id"]

    # 2) STARS 系列（幂等）
    series_rows = unwrap(client.get("/api/admin/series"))
    stars = next((s for s in series_rows if s["en"] == "STARS"), None)
    if stars is None:
        stars = unwrap(client.post("/api/admin/series", json={**SERIES_STARS, "cover": ""}))
        print("✓ 系列「STARS」")

    # 3) 上传图片
    urls: dict[str, str] = {}
    for f in sorted(asset_dir.iterdir()):
        if f.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        mime = mimetypes.guess_type(f.name)[0] or "image/jpeg"
        with f.open("rb") as fh:
            urls[f.name] = unwrap(client.post(
                "/api/v1/uploads", files={"file": (f.name, fh, mime)}))["url"]
        print(f"✓ 上传 {f.name} → {urls[f.name]}")

    # STARS 封面用黑色星标裤
    if not stars.get("cover") and "star-pants-black.jpg" in urls:
        unwrap(client.put(f"/api/admin/series/{stars['id']}", json={
            "name": stars["name"], "en": stars["en"], "subtitle": stars["subtitle"],
            "cover": urls["star-pants-black.jpg"], "cover_tint": stars["cover_tint"],
            "sort": stars["sort"], "status": 1}))
        print("✓ STARS 封面已挂")

    # 4) 商品（按款号幂等）
    for p in PRODUCTS:
        existing = unwrap(client.get("/api/admin/products", params={"q": p["code"]}))
        if existing["total"] > 0:
            print(f"- 商品「{p['name']}」({p['code']}) 已存在，跳过")
            continue
        skus, images = [], []
        for ci, (cname, chex, files) in enumerate(p["colors"]):
            for size in p.get("sizes", SIZES):
                skus.append({"color_index": ci, "color_name": cname, "color_hex": chex,
                             "size": size, "price": p["price"], "stock": 8})
            for k, fname in enumerate(files):
                images.append({"color_index": ci, "url": urls[fname], "sort": len(images)})
        unwrap(client.post("/api/admin/products", json={
            "category_id": leaf_id[p["cat"]],
            "series_id": stars["id"] if p["series"] else None,
            "name": p["name"], "sub": p["name"], "code": p["code"], "en_model": p["code"],
            "brief": p["brief"], "detail": p["brief"], "bullets": p["bullets"],
            "badge": None, "featured": p["featured"], "has_video": False,
            "original_price": None, "sort": 0, "status": 1,
            "skus": skus, "images": images,
        }))
        print(f"✓ 商品「{p['name']}」({p['code']}) 已建档，{len(skus)} SKU / {len(images)} 图")

    # 5) 下架 AURELLE 演示数据（商品/一级品类/系列），幂等
    page = unwrap(client.get("/api/admin/products", params={"page_size": 100}))
    for item in page["items"]:
        if str(item.get("code", "")).startswith("AU433") and item["status"] == 1:
            unwrap(client.post(f"/api/admin/products/{item['id']}/status", json={"status": 0}))
            print(f"↓ 下架 AURELLE 商品「{item['name']}」")
    cats = unwrap(client.get("/api/admin/categories"))
    for c in cats:
        if c["parent_id"] is None and c["name"] in AURELLE_TOPS and c["status"] == 1:
            unwrap(client.put(f"/api/admin/categories/{c['id']}", json={
                "name": c["name"], "en": c["en"], "parent_id": None, "sort": 50, "status": 0}))
            print(f"↓ 隐藏 AURELLE 品类「{c['name']}」")
    for s in unwrap(client.get("/api/admin/series")):
        if s["en"] in AURELLE_SERIES_EN and s["status"] == 1:
            unwrap(client.put(f"/api/admin/series/{s['id']}", json={
                "name": s["name"], "en": s["en"], "subtitle": s["subtitle"], "cover": s["cover"],
                "cover_tint": s["cover_tint"], "sort": s["sort"] + 50, "status": 0}))
            print(f"↓ 隐藏 AURELLE 系列「{s['en']}」")

    # 6) 汇总
    tree = unwrap(client.get("/api/v1/categories"))
    prods = unwrap(client.get("/api/v1/products", params={"page_size": 50}))
    print("\n—— C 端现状 ——")
    print("品类树：", " / ".join(f"{t['name']}({len(t['children'])})" for t in tree))
    print(f"在售商品 {prods['total']} 款：")
    for it in prods["items"]:
        print(f"  {it['code'] or it['en_model']}  {it['name']}  ¥{it['price'] / 100:,.0f}")


if __name__ == "__main__":
    main()
