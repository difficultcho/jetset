"""管理后台内容域：品类级联 / 商品新字段 / 系列 / 门店 / 品牌内容。"""
from tests.test_admin import admin_login


async def test_admin_categories_flat_tree(client):
    h = await admin_login(client)
    cats = (await client.get("/api/admin/categories", headers=h)).json()["data"]
    tops = [c for c in cats if c["parent_id"] is None]
    leaves = [c for c in cats if c["parent_id"] is not None]
    assert len(tops) >= 7 and leaves
    # 二级带父级名，供级联/分组展示
    heels = next(c for c in leaves if c["name"] == "高跟鞋")
    assert heels["parent_name"] == "鞋履"


async def test_series_crud_and_c_end(client):
    h = await admin_login(client)
    created = (await client.post("/api/admin/series", headers=h, json={
        "name": "2027早春度假", "en": "RESORT 2027", "subtitle": "度假系列",
        "cover": "/uploads/resort.jpg", "sort": 50})).json()["data"]
    sid = created["id"]

    # C 端可见（status=1）
    pub = (await client.get("/api/v1/series")).json()["data"]
    mine = next(s for s in pub if s["id"] == sid)
    assert mine["en"] == "RESORT 2027" and mine["cover"] == "/uploads/resort.jpg"

    # 下架后 C 端消失，管理端仍可见
    created["status"] = 0
    await client.put(f"/api/admin/series/{sid}", headers=h, json=created)
    pub = (await client.get("/api/v1/series")).json()["data"]
    assert not any(s["id"] == sid for s in pub)
    all_rows = (await client.get("/api/admin/series", headers=h)).json()["data"]
    assert any(s["id"] == sid for s in all_rows)

    # 有商品归属时禁止删除
    seeded = next(s for s in all_rows if s["product_count"] > 0)
    resp = await client.delete(f"/api/admin/series/{seeded['id']}", headers=h)
    assert resp.status_code == 400

    # 空系列可删除
    resp = await client.delete(f"/api/admin/series/{sid}", headers=h)
    assert resp.status_code == 200


async def test_product_new_fields_roundtrip(client):
    h = await admin_login(client)
    cats = (await client.get("/api/admin/categories", headers=h)).json()["data"]
    leaf = next(c for c in cats if c["parent_name"] == "鞋履")
    series = (await client.get("/api/admin/series", headers=h)).json()["data"][0]

    payload = {
        "category_id": leaf["id"], "series_id": series["id"],
        "name": "SOLEIL 测试缎面高跟鞋", "sub": "缎面高跟鞋", "code": "AU999TEST01",
        "brief": "简介", "detail": "详情",
        "bullets": ["意大利制造", "真丝缎面", "鞋跟高度 8.5cm"],
        "badge": "SALE", "featured": True, "has_video": True,
        "original_price": 1280000, "sort": 88, "status": 1,
        "skus": [{"color_index": 0, "color_name": "象牙白", "color_hex": "#f4ede2",
                  "size": "37", "price": 640000, "stock": 3}],
        "images": [{"color_index": 0, "url": "/uploads/heel.jpg", "sort": 0}],
    }
    spu_id = (await client.post("/api/admin/products", headers=h, json=payload)).json()["data"]["id"]

    # 管理端详情完整回读
    d = (await client.get(f"/api/admin/products/{spu_id}", headers=h)).json()["data"]
    assert d["sub"] == "缎面高跟鞋" and d["code"] == "AU999TEST01"
    assert d["series_id"] == series["id"] and d["has_video"] is True
    assert d["original_price"] == 1280000 and d["bullets"][2] == "鞋跟高度 8.5cm"

    # C 端详情透出新字段
    c = (await client.get(f"/api/v1/products/{spu_id}")).json()["data"]
    assert c["code"] == "AU999TEST01" and c["series"]["id"] == series["id"]
    assert c["original_price"] == 1280000 and len(c["bullets"]) == 3

    # 更新：摘掉系列、清空划线价
    payload["series_id"] = None
    payload["original_price"] = None
    await client.put(f"/api/admin/products/{spu_id}", headers=h, json=payload)
    d = (await client.get(f"/api/admin/products/{spu_id}", headers=h)).json()["data"]
    assert d["series_id"] is None and d["original_price"] is None

    # 不存在的系列被拒
    payload["series_id"] = 999999
    resp = await client.put(f"/api/admin/products/{spu_id}", headers=h, json=payload)
    assert resp.status_code == 400

    # 管理端列表可按款号搜索
    page = (await client.get("/api/admin/products", headers=h,
                             params={"q": "AU999TEST01"})).json()["data"]
    assert page["total"] == 1 and page["items"][0]["code"] == "AU999TEST01"

    # 收尾下架，不影响 C 端目录类用例的数量断言
    await client.post(f"/api/admin/products/{spu_id}/status", headers=h, json={"status": 0})


async def test_store_crud_and_c_end(client):
    h = await admin_login(client)
    created = (await client.post("/api/admin/stores", headers=h, json={
        "name": "深圳湾万象城精品店", "short_name": "深圳湾万象城",
        "province": "广东省", "city": "深圳市", "address": "深圳湾万象城 L1",
        "tel": "0755-88888888", "business_hours": "10:00-22:00",
        "images": ["/uploads/sz1.jpg", "/uploads/sz2.jpg"],
        "lat": 22.52, "lng": 113.94})).json()["data"]
    sid = created["id"]

    # C 端列表 + 省市筛选 + 详情
    pub = (await client.get("/api/v1/stores", params={"province": "广东省"})).json()["data"]
    assert any(s["id"] == sid for s in pub)
    detail = (await client.get(f"/api/v1/stores/{sid}")).json()["data"]
    assert detail["images"] == ["/uploads/sz1.jpg", "/uploads/sz2.jpg"]
    regions = (await client.get("/api/v1/stores/regions")).json()["data"]
    assert "广东省" in regions["provinces"]

    # 下架后 C 端消失
    created["status"] = 0
    await client.put(f"/api/admin/stores/{sid}", headers=h, json=created)
    pub = (await client.get("/api/v1/stores")).json()["data"]
    assert not any(s["id"] == sid for s in pub)

    resp = await client.delete(f"/api/admin/stores/{sid}", headers=h)
    assert resp.status_code == 200


async def test_brand_post_crud_and_c_end(client):
    h = await admin_login(client)
    created = (await client.post("/api/admin/brand/posts", headers=h, json={
        "type": "project", "title": "N.05 SKI CAPSULE", "subtitle": "滑雪胶囊企划",
        "cover": "/uploads/ski.jpg",
        "body": [{"kind": "image", "img": "/uploads/ski-1.jpg", "ratio": "3/2"},
                 {"kind": "text", "value": "山巅之上。"}],
        "sort": 99})).json()["data"]
    pid = created["id"]

    # C 端卡片 + 详情（body 图文块，图片块用 img 键）
    cards = (await client.get("/api/v1/brand/posts", params={"type": "project"})).json()["data"]
    assert any(p["id"] == pid and p["cover"] == "/uploads/ski.jpg" for p in cards)
    detail = (await client.get(f"/api/v1/brand/posts/{pid}")).json()["data"]
    assert detail["body"][0]["kind"] == "image" and detail["body"][0]["img"] == "/uploads/ski-1.jpg"

    # 管理端按类型筛选
    rows = (await client.get("/api/admin/brand/posts", headers=h,
                             params={"type": "project"})).json()["data"]
    assert all(p["type"] == "project" for p in rows)

    # 非法类型被拒
    resp = await client.post("/api/admin/brand/posts", headers=h,
                             json={"type": "blog", "title": "x"})
    assert resp.status_code == 422

    # 下架后 C 端消失
    created["status"] = 0
    await client.put(f"/api/admin/brand/posts/{pid}", headers=h, json=created)
    cards = (await client.get("/api/v1/brand/posts", params={"type": "project"})).json()["data"]
    assert not any(p["id"] == pid for p in cards)

    resp = await client.delete(f"/api/admin/brand/posts/{pid}", headers=h)
    assert resp.status_code == 200
