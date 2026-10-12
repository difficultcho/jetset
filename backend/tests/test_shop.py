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


async def test_series_entries_include_childless_top_category(client):
    """商品可以直接挂在「还没建二级类目」的一级类目上（管理端就是这么给选的）。

    这种类目自己就是叶子，向上归并到它自己。早期实现只认 parent_id 非空的类目，
    导致这类商品在商城里彻底摸不到——系列选中后右侧一片空白。
    """
    h = await admin_login(client)

    # 一个没有任何二级类目的一级类目
    top = (await client.post("/api/admin/categories", headers=h, json={
        "name": "无子类目一级", "en": "FLAT", "parent_id": None, "sort": 90})).json()["data"]
    assert top["parent_id"] is None
    se = (await client.post("/api/admin/series", headers=h, json={
        "name": "平铺系列", "en": "FLAT SERIES", "sort": 90})).json()["data"]

    # 在售商品直接挂在这个一级类目上
    spu = (await client.post("/api/admin/products", headers=h, json={
        "category_id": top["id"], "series_id": se["id"], "name": "平铺商品",
        "code": "FLAT001", "status": 1,
        "skus": [{"color_index": 0, "color_name": "黑", "size": "均码",
                  "price": 100000, "stock": 3}]})).json()["data"]

    await client.put("/api/admin/shop/menus", headers=h, json={
        "kind": "series", "ref_id": se["id"], "sort": 90, "status": 1, "banners": []})

    data = (await client.get("/api/v1/shop")).json()["data"]
    sm = next(m for m in data["menus"] if m["key"] == f"series-{se['id']}")
    # 关键：入口派生出来了，而不是空列表
    assert [e["title"] for e in sm["entries"]] == ["无子类目一级"]
    assert sm["entries"][0]["filter"] == {"series": se["id"], "cat": "无子类目一级"}

    # 入口的过滤条件真能筛到这个商品（否则入口点进去还是空列表）
    got = (await client.get("/api/v1/products", params={
        "cat": "无子类目一级", "series": se["id"]})).json()["data"]
    assert [it["id"] for it in got["items"]] == [spu["id"]]

    # 收尾：不影响其他用例的菜单/数量断言
    await client.post(f"/api/admin/products/{spu['id']}/status", headers=h, json={"status": 0})
    rows = (await client.get("/api/admin/shop/menus", headers=h)).json()["data"]
    mine = next(r for r in rows if r["kind"] == "series" and r["ref_id"] == se["id"])
    await client.delete(f"/api/admin/shop/menus/{mine['id']}", headers=h)
    await client.put(f"/api/admin/categories/{top['id']}", headers=h, json={
        "name": "无子类目一级", "en": "FLAT", "parent_id": None, "sort": 90, "status": 0})


async def test_subcategory_cover_is_first_product_image(client):
    """子类方块的封面：综合排序第一个上架商品的首图。空子类、或第一个商品没图，都是 null。"""
    h = await admin_login(client)

    parent = (await client.post("/api/admin/categories", headers=h, json={
        "name": "方块父级", "en": "TILES", "parent_id": None, "sort": 80})).json()["data"]
    filled = (await client.post("/api/admin/categories", headers=h, json={
        "name": "有货子类", "en": "FILLED", "parent_id": parent["id"], "sort": 1})).json()["data"]
    blank = (await client.post("/api/admin/categories", headers=h, json={
        "name": "无图子类", "en": "NOIMG", "parent_id": parent["id"], "sort": 2})).json()["data"]
    empty = (await client.post("/api/admin/categories", headers=h, json={
        "name": "空子类", "en": "EMPTY", "parent_id": parent["id"], "sort": 3})).json()["data"]

    sku = {"color_index": 0, "color_name": "黑", "size": "均码", "price": 10000, "stock": 1}

    async def add(cat_id, name, sort, images, status=1):
        return (await client.post("/api/admin/products", headers=h, json={
            "category_id": cat_id, "name": name, "code": name, "status": status, "sort": sort,
            "skus": [sku], "images": images,
        })).json()["data"]

    # 更小的 id、更大的 sort，不能抢封面
    later = await add(filled["id"], "方块较后", 5, [
        {"color_index": 0, "url": "/uploads/tile-later.jpg", "sort": 0}])
    # 下架商品即使 sort 更小也不算
    hidden = await add(filled["id"], "方块下架", 0, [
        {"color_index": 0, "url": "/uploads/tile-hidden.jpg", "sort": 0}], status=0)
    first = await add(filled["id"], "方块第一", 1, [
        {"color_index": 0, "url": "/uploads/tile-second.jpg", "sort": 1},
        {"color_index": 0, "url": "/uploads/tile-first.jpg", "sort": 0},
    ])
    # 这个子类里 sort 最小的商品没有图，不改用后面那件的图
    noimg = await add(blank["id"], "方块无图", 0, [])
    skipped = await add(blank["id"], "方块无图之后", 1, [
        {"color_index": 0, "url": "/uploads/tile-skip.jpg", "sort": 0}])

    data = (await client.get("/api/v1/shop")).json()["data"]
    menu = next(m for m in data["menus"] if m["key"] == f"cat-{parent['id']}")
    by = {e["title"]: e for e in menu["entries"]}
    assert [e["title"] for e in menu["entries"]] == ["有货子类", "无图子类", "空子类"]
    assert by["有货子类"]["image"] == "/uploads/tile-first.jpg"
    assert by["有货子类"]["filter"] == {"cat": "有货子类"}
    assert by["无图子类"]["image"] is None
    assert by["空子类"]["image"] is None
    # 「全部XX」不是入口封面，菜单本身不带 image
    assert "image" not in menu

    for spu in (later, hidden, first, noimg, skipped):
        await client.post(f"/api/admin/products/{spu['id']}/status", headers=h, json={"status": 0})
    for cat, name, en, parent_id, sort in (
        (filled, "有货子类", "FILLED", parent["id"], 1),
        (blank, "无图子类", "NOIMG", parent["id"], 2),
        (empty, "空子类", "EMPTY", parent["id"], 3),
        (parent, "方块父级", "TILES", None, 80),
    ):
        await client.put(f"/api/admin/categories/{cat['id']}", headers=h, json={
            "name": name, "en": en, "parent_id": parent_id, "sort": sort, "status": 0})
