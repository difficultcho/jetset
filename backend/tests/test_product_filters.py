"""商品列表筛选：筛选项接口、尺码多选、价格区间。"""


async def test_filter_options(client):
    data = (await client.get("/api/v1/products/filters")).json()["data"]
    keys = [g["key"] for g in data["groups"]]
    assert "price" in keys
    size = next(g for g in data["groups"] if g["key"] == "size")
    assert size["multi"] is True
    labels = [o["label"] for o in size["opts"]]
    # 按服装惯例排序，不是字典序（S 在 M 前、M 在 L 前）
    order = {l: i for i, l in enumerate(labels)}
    for a, b in (("S", "M"), ("M", "L"), ("L", "XL")):
        if a in order and b in order:
            assert order[a] < order[b], f"{a} 应排在 {b} 之前，实得 {labels}"
    # 价格档位互不重叠且升序
    rng = [tuple(int(x) for x in o["v"].split("-")) for o in
           next(g for g in data["groups"] if g["key"] == "price")["opts"]]
    for (lo1, hi1), (lo2, _) in zip(rng, rng[1:]):
        assert lo1 < hi1 < lo2


async def test_filters_route_not_shadowed(client):
    """/products/filters 必须排在 /products/{spu_id} 之前，否则会被当成商品 id 解析。"""
    assert (await client.get("/api/v1/products/filters")).status_code == 200
    assert (await client.get("/api/v1/products/999999")).status_code == 404


async def test_filter_by_size(client):
    all_items = (await client.get("/api/v1/products", params={"page_size": 100})).json()["data"]["items"]
    opts = (await client.get("/api/v1/products/filters")).json()["data"]["groups"]
    sizes = [o["v"] for o in next(g for g in opts if g["key"] == "size")["opts"]]
    assert sizes

    one = (await client.get("/api/v1/products",
                            params={"size": sizes[0], "page_size": 100})).json()["data"]
    assert one["total"] <= len(all_items)
    # 命中的每件商品都确实有该尺码
    for it in one["items"]:
        d = (await client.get(f"/api/v1/products/{it['id']}")).json()["data"]
        assert sizes[0] in d["sizes"]

    # 多选是并集：结果不小于单选
    if len(sizes) > 1:
        multi = (await client.get("/api/v1/products", params={
            "size": f"{sizes[0]},{sizes[1]}", "page_size": 100})).json()["data"]
        assert multi["total"] >= one["total"]

    # 不存在的尺码 → 空结果，不报错
    none = (await client.get("/api/v1/products", params={"size": "不存在的码"})).json()["data"]
    assert none["total"] == 0


async def test_filter_by_price(client):
    items = (await client.get("/api/v1/products", params={"page_size": 100})).json()["data"]["items"]
    prices = sorted(i["price"] for i in items)
    mid = prices[len(prices) // 2]

    low = (await client.get("/api/v1/products",
                            params={"price_max": mid, "page_size": 100})).json()["data"]
    assert low["total"] > 0 and all(i["price"] <= mid for i in low["items"])

    high = (await client.get("/api/v1/products",
                             params={"price_min": mid, "page_size": 100})).json()["data"]
    assert all(i["price"] >= mid for i in high["items"])


async def test_filters_compose_with_category(client):
    """筛选与既有的品类/系列条件是叠加关系，不互相覆盖。"""
    cats = (await client.get("/api/v1/categories")).json()["data"]
    top = cats[0]["name"]
    base = (await client.get("/api/v1/products",
                             params={"cat": top, "page_size": 100})).json()["data"]
    sizes = [o["v"] for o in next(
        g for g in (await client.get("/api/v1/products/filters")).json()["data"]["groups"]
        if g["key"] == "size")["opts"]]
    both = (await client.get("/api/v1/products", params={
        "cat": top, "size": sizes[0], "page_size": 100})).json()["data"]
    assert both["total"] <= base["total"]
    base_ids = {i["id"] for i in base["items"]}
    assert all(i["id"] in base_ids for i in both["items"])
