"""配置化页面：块校验、走马灯数据源解析、链接解析、停用回退。"""
from app.db import SessionFactory
from app.models.cms import Page
from tests.test_admin import admin_login


async def test_fixed_page_title_falls_back(client):
    """历史数据里固定页 title 可能是空串（早期版本写入），读取侧须回退到默认标题。"""
    h = await admin_login(client)
    await client.put("/api/admin/pages/home", headers=h, json={"blocks": [], "status": 1})

    async with SessionFactory() as s:          # 直接把库改成脏状态
        p = await s.get(Page, "home")
        p.title = ""
        await s.commit()

    rows = (await client.get("/api/admin/pages", headers=h)).json()["data"]
    home = next(r for r in rows if r["key"] == "home")
    assert home["title"] == "首页" and home["fixed"] is True
    assert (await client.get("/api/admin/pages/home", headers=h)).json()["data"]["title"] == "首页"


async def test_page_home_configure_and_resolve(client):
    h = await admin_login(client)

    # 备好素材：两个在售商品（手动选品用，故意倒序）+ 一个叶子品类 + 一个内容页（链接目标）
    prods = (await client.get("/api/admin/products", headers=h,
                              params={"page_size": 100})).json()["data"]["items"]
    on_sale = [p for p in prods if p["status"] == 1]
    assert len(on_sale) >= 2
    manual_ids = [on_sale[1]["id"], on_sale[0]["id"]]

    cats = (await client.get("/api/admin/categories", headers=h)).json()["data"]
    leaf = next(c for c in cats if c["parent_id"] is not None and c["status"] == 1)
    target = (await client.post("/api/admin/pages", headers=h, json={
        "title": "链接目标页",
        "blocks": [{"kind": "text", "preset": "para", "text": "内容页"}]})).json()["data"]
    tkey = target["key"]

    # 非法块被拒
    resp = await client.put("/api/admin/pages/home", headers=h,
                            json={"blocks": [{"kind": "widget"}], "status": 1})
    assert resp.status_code == 400
    resp = await client.put("/api/admin/pages/home", headers=h, json={
        "blocks": [{"kind": "carousel", "source": "manual", "spu_ids": []}], "status": 1})
    assert resp.status_code == 400

    # 链接行：左右至少一侧文字
    resp = await client.put("/api/admin/pages/home", headers=h, json={
        "blocks": [{"kind": "linkrow", "left": {"text": ""}, "right": {"text": ""}}], "status": 1})
    assert resp.status_code == 400

    # 保存一页各种块（含链接行：左跳品类列表、右跳内容页）
    blocks = [
        {"kind": "image", "img": "/uploads/hero.jpg", "ratio": "hero", "inset": False,
         "link": {"kind": "list", "category_id": leaf["id"]}},
        {"kind": "linkrow",
         "left": {"text": "探索系列", "link": {"kind": "list", "category_id": leaf["id"]}},
         "right": {"text": "品牌故事", "link": {"kind": "page", "key": tkey}}},
        {"kind": "text", "preset": "para", "underline": True, "text": "品牌故事",
         "align": "right", "link": {"kind": "page", "key": tkey}},
        {"kind": "carousel", "source": "manual", "spu_ids": manual_ids, "count": 6},
        {"kind": "video", "src": "/uploads/b.mp4", "poster": "/uploads/p.jpg", "ratio": "3/3.4"},
        {"kind": "text", "preset": "para", "text": "山巅之上。",
         "link": {"kind": "page", "key": tkey}},
        {"kind": "carousel", "source": "category", "category_id": leaf["id"], "count": 4},
        {"kind": "linkrow", "left": {"text": "仅左链接", "link": None}, "right": {"text": ""}},
    ]
    resp = await client.put("/api/admin/pages/home", headers=h,
                            json={"blocks": blocks, "status": 1})
    assert resp.status_code == 200

    # C 端解析：走马灯出商品卡（手选保序）、链接解析出导航参数、视频不带链接
    data = (await client.get("/api/v1/pages/home")).json()["data"]
    b = data["blocks"]
    page_link = {"kind": "page", "key": tkey, "title": "链接目标页"}
    assert b[0]["link"] == {"kind": "list", "cat": leaf["name"], "title": leaf["name"]}
    # 链接行左右各自解析；仅左块右侧为 None
    assert b[1]["left"]["text"] == "探索系列" and b[1]["left"]["link"]["cat"] == leaf["name"]
    assert b[1]["right"]["link"] == page_link
    assert b[2]["link"] == page_link
    assert [it["id"] for it in b[3]["items"]] == manual_ids
    assert "image" in b[3]["items"][0] and "price" in b[3]["items"][0]
    assert b[4]["link"] is None
    assert b[5]["link"] == page_link
    assert isinstance(b[6]["items"], list)
    assert b[7]["left"]["text"] == "仅左链接" and b[7]["left"]["link"] is None and b[7]["right"] is None

    # 停用 → C 端回落（data 为 None）
    resp = await client.put("/api/admin/pages/home", headers=h,
                            json={"blocks": blocks, "status": 0})
    assert resp.status_code == 200
    assert (await client.get("/api/v1/pages/home")).json()["data"] is None

    # 删内容页 → 引用它的链接解析降级为 None（先把 home 恢复启用再验证）
    await client.put("/api/admin/pages/home", headers=h, json={"blocks": blocks, "status": 1})
    assert (await client.delete(f"/api/admin/pages/{tkey}", headers=h)).status_code == 200
    data = (await client.get("/api/v1/pages/home")).json()["data"]
    assert data["blocks"][2]["link"] is None       # 文本块指向已删页 → 不可点
    assert data["blocks"][1]["right"]["link"] is None

    # 固定页不可删；未定义 key 管理端 404
    assert (await client.delete("/api/admin/pages/home", headers=h)).status_code == 400
    assert (await client.get("/api/admin/pages/nope", headers=h)).status_code == 404

    # 收尾：停用 home，避免影响其他用例
    await client.put("/api/admin/pages/home", headers=h, json={"blocks": blocks, "status": 0})


async def test_fixed_page_stub_has_no_nulls(client):
    """固定页未落库时返回的是内存壳，SQLAlchemy 列默认值尚未生效。
    若把 None 透传给管理端，原样回传就会撞 PageIn 类型约束报 422。"""
    h = await admin_login(client)
    async with SessionFactory() as s:          # 制造「从未保存过」的状态
        p = await s.get(Page, "brand")
        if p is not None:
            await s.delete(p)
            await s.commit()

    data = (await client.get("/api/admin/pages/brand", headers=h)).json()["data"]
    for field in ("title", "sort", "status", "blocks"):
        assert data[field] is not None, f"{field} 不该是 None"
    assert data["status"] == 1

    # 关键：原样回传必须能存下来，而不是 422
    resp = await client.put("/api/admin/pages/brand", headers=h, json={
        "title": data["title"], "sort": data["sort"],
        "status": data["status"], "blocks": data["blocks"]})
    assert resp.status_code == 200, resp.text


async def test_underline_is_orthogonal_not_a_preset(client):
    """下划线从排版预设拆成独立开关：link 不再是合法 preset，
    underline 可搭配任意 preset 并原样透到 C 端。"""
    h = await admin_login(client)

    resp = await client.put("/api/admin/pages/home", headers=h, json={
        "blocks": [{"kind": "text", "preset": "link", "text": "旧排版"}], "status": 1})
    assert resp.status_code == 400

    blocks = [
        {"kind": "text", "preset": "para", "underline": True, "text": "带下划线的正文"},
        {"kind": "text", "preset": "eyebrow", "underline": False, "text": "图注"},
        {"kind": "text", "preset": "quote", "underline": True, "text": "带下划线的引文"},
    ]
    assert (await client.put("/api/admin/pages/home", headers=h,
                             json={"blocks": blocks, "status": 1})).status_code == 200

    got = (await client.get("/api/v1/pages/home")).json()["data"]["blocks"]
    assert [b["underline"] for b in got] == [True, False, True]
    assert [b["preset"] for b in got] == ["para", "eyebrow", "quote"]

    await client.put("/api/admin/pages/home", headers=h, json={"blocks": blocks, "status": 0})
