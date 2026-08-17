"""商城配置：左菜单两组来源、图片跳链校验与解析、下钻入口派生。"""
from tests.test_admin import admin_login


async def test_shop_menu_config_and_resolve(client):
    h = await admin_login(client)

    series = (await client.get("/api/admin/series", headers=h)).json()["data"]
    s = next(x for x in series if x["status"] == 1)
    cats = (await client.get("/api/admin/categories", headers=h)).json()["data"]
    top = next(c for c in cats if c["parent_id"] is None and c["status"] == 1)
    leaf = next(c for c in cats if c["parent_id"] is not None and c["status"] == 1)
    target = (await client.post("/api/admin/pages", headers=h, json={
        "title": "商城内容页", "blocks": [{"kind": "text", "preset": "para", "text": "x"}],
    })).json()["data"]

    # 未配置时：左菜单只有一级类目，且每项自带二级类目作为下钻入口
    data = (await client.get("/api/v1/shop")).json()["data"]
    assert all(m["kind"] == "category" for m in data["menus"])
    tm = next(m for m in data["menus"] if m["id"] == top["id"])
    assert tm["filter"] == {"cat": top["name"]}
    assert tm["banners"] == []
    assert all(e["filter"].keys() == {"cat"} for e in tm["entries"])

    # 图片跳链校验：未传图 / 非法 kind 都拒
    bad = await client.put("/api/admin/shop/menus", headers=h, json={
        "kind": "series", "ref_id": s["id"], "banners": [{"img": ""}]})
    assert bad.status_code == 400
    bad = await client.put("/api/admin/shop/menus", headers=h, json={
        "kind": "series", "ref_id": s["id"],
        "banners": [{"img": "/uploads/a.jpg", "link": {"kind": "post", "post_id": 1}}]})
    assert bad.status_code == 400
    # 只能挂一级类目
    bad = await client.put("/api/admin/shop/menus", headers=h, json={
        "kind": "category", "ref_id": leaf["id"], "banners": []})
    assert bad.status_code == 400
    # 文字标题超长被拒
    bad = await client.put("/api/admin/shop/menus", headers=h, json={
        "kind": "series", "ref_id": s["id"],
        "banners": [{"img": "/uploads/a.jpg", "title": "字" * 61}]})
    assert bad.status_code == 400

    # 上部自定义项：挂系列，配两张图（一张跳内容页，一张跳商品列表）
    created = (await client.put("/api/admin/shop/menus", headers=h, json={
        "kind": "series", "ref_id": s["id"], "title": "成衣系列", "en": "READY TO WEAR",
        "sort": 1, "status": 1,
        "banners": [
            {"img": "/uploads/a.jpg", "title": "  秀场大片  ",
             "link": {"kind": "page", "key": target["key"]}},
            {"img": "/uploads/b.jpg", "link": {"kind": "list", "category_id": leaf["id"]}},
            {"img": "/uploads/c.jpg", "title": "", "link": None},
        ]})).json()["data"]
    assert created["id"] > 0

    data = (await client.get("/api/v1/shop")).json()["data"]
    sm = data["menus"][0]                      # 自定义项排在一级类目之前
    assert sm["key"] == f"series-{s['id']}" and sm["title"] == "成衣系列"
    assert sm["filter"] == {"series": s["id"]}
    assert sm["banners"][0]["link"] == {"kind": "page", "key": target["key"], "title": "商城内容页"}
    assert sm["banners"][1]["link"]["cat"] == leaf["name"]
    assert sm["banners"][2]["link"] is None    # 不跳转
    # 文字标题：去空白后原样透出；没填的补空串，C 端据此决定是否渲染
    assert sm["banners"][0]["title"] == "秀场大片"
    assert sm["banners"][1]["title"] == "" and sm["banners"][2]["title"] == ""
    # 系列的下钻入口 = 该系列在售商品涉及的一级类目（去重派生），带上系列限定
    for e in sm["entries"]:
        assert e["filter"]["series"] == s["id"] and "cat" in e["filter"]

    # upsert：同一 (kind, ref_id) 再存是更新不是新增
    again = (await client.put("/api/admin/shop/menus", headers=h, json={
        "kind": "series", "ref_id": s["id"], "title": "改名了", "banners": []})).json()["data"]
    assert again["id"] == created["id"]
    rows = (await client.get("/api/admin/shop/menus", headers=h)).json()["data"]
    assert len([r for r in rows if r["kind"] == "series" and r["ref_id"] == s["id"]]) == 1

    # 一级类目：管理端以占位行给出（id=0），保存后才落库
    stub = next(r for r in rows if r["kind"] == "category" and r["ref_id"] == top["id"])
    assert stub["id"] == 0
    saved = (await client.put("/api/admin/shop/menus", headers=h, json={
        "kind": "category", "ref_id": top["id"],
        "banners": [{"img": "/uploads/t.jpg", "link": {"kind": "page", "key": target["key"]}}],
    })).json()["data"]
    assert saved["id"] > 0
    data = (await client.get("/api/v1/shop")).json()["data"]
    tm = next(m for m in data["menus"] if m["key"] == f"cat-{top['id']}")
    assert len(tm["banners"]) == 1

    # 目标页被删 → 跳转降级为 None，图片仍在（块不可点，不整块消失）
    assert (await client.delete(f"/api/admin/pages/{target['key']}", headers=h)).status_code == 200
    data = (await client.get("/api/v1/shop")).json()["data"]
    tm = next(m for m in data["menus"] if m["key"] == f"cat-{top['id']}")
    assert len(tm["banners"]) == 1 and tm["banners"][0]["link"] is None

    # 一级类目不可从菜单移除；自定义项可以
    assert (await client.delete(f"/api/admin/shop/menus/{saved['id']}", headers=h)).status_code == 400
    assert (await client.delete(f"/api/admin/shop/menus/{created['id']}", headers=h)).status_code == 200
    data = (await client.get("/api/v1/shop")).json()["data"]
    assert all(m["kind"] == "category" for m in data["menus"])
