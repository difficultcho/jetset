"""配置化页面：块校验、走马灯数据源解析、链接解析、停用回退。"""
from tests.test_admin import admin_login


async def test_page_home_configure_and_resolve(client):
    h = await admin_login(client)

    # 备好素材：两个在售商品（手动选品用，故意倒序）+ 一个叶子品类 + 一篇内容帖
    prods = (await client.get("/api/admin/products", headers=h,
                              params={"page_size": 100})).json()["data"]["items"]
    on_sale = [p for p in prods if p["status"] == 1]
    assert len(on_sale) >= 2
    manual_ids = [on_sale[1]["id"], on_sale[0]["id"]]

    cats = (await client.get("/api/admin/categories", headers=h)).json()["data"]
    leaf = next(c for c in cats if c["parent_id"] is not None and c["status"] == 1)
    posts = (await client.get("/api/admin/brand/posts", headers=h)).json()["data"]
    post = next(p for p in posts if p["status"] == 1 and not p["parent_id"])

    # 非法块被拒
    resp = await client.put("/api/admin/pages/home", headers=h,
                            json={"blocks": [{"kind": "widget"}], "status": 1})
    assert resp.status_code == 400
    resp = await client.put("/api/admin/pages/home", headers=h, json={
        "blocks": [{"kind": "carousel", "source": "manual", "spu_ids": []}], "status": 1})
    assert resp.status_code == 400

    # 保存一页四种块
    blocks = [
        {"kind": "image", "img": "/uploads/hero.jpg", "ratio": "hero", "inset": False,
         "link": {"kind": "list", "category_id": leaf["id"]}},
        {"kind": "text", "preset": "link", "text": "探索广告大片", "align": "right",
         "link": {"kind": "campaign"}},
        {"kind": "carousel", "source": "manual", "spu_ids": manual_ids, "count": 6},
        {"kind": "video", "src": "/uploads/b.mp4", "poster": "/uploads/p.jpg", "ratio": "3/3.4"},
        {"kind": "text", "preset": "para", "text": "山巅之上。",
         "link": {"kind": "post", "post_id": post["id"]}},
        {"kind": "carousel", "source": "category", "category_id": leaf["id"], "count": 4},
    ]
    resp = await client.put("/api/admin/pages/home", headers=h,
                            json={"blocks": blocks, "status": 1})
    assert resp.status_code == 200

    # C 端解析：走马灯出商品卡（手选保序）、链接解析出导航参数、视频不带链接
    data = (await client.get("/api/v1/pages/home")).json()["data"]
    b = data["blocks"]
    assert b[0]["link"] == {"kind": "list", "cat": leaf["name"], "title": leaf["name"]}
    assert b[1]["link"] == {"kind": "campaign"}
    assert [it["id"] for it in b[2]["items"]] == manual_ids
    assert "image" in b[2]["items"][0] and "price" in b[2]["items"][0]
    assert b[3]["link"] is None
    assert b[4]["link"] == {"kind": "post", "post_id": post["id"]}
    assert isinstance(b[5]["items"], list)

    # 停用 → C 端回落（data 为 None）；收尾保持停用，避免影响其他用例
    resp = await client.put("/api/admin/pages/home", headers=h,
                            json={"blocks": blocks, "status": 0})
    assert resp.status_code == 200
    assert (await client.get("/api/v1/pages/home")).json()["data"] is None

    # 未定义的页面 key：管理端 404
    assert (await client.get("/api/admin/pages/nope", headers=h)).status_code == 404
