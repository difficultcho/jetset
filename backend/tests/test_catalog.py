async def test_home(client):
    resp = await client.get("/api/v1/home")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["banners"]) == 3
    assert data["banners"][0]["title"] == "山海无界  陪伴无休"
    assert len(data["hot"]) == 5
    assert data["featured"]["en_model"] == "TRAILVA 1.0"
    assert len(data["grid"]) == 5  # 8 个商品，grid 从第 4 个开始


async def test_categories(client):
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()["data"]]
    assert names == ["冲锋衣", "包类", "短裤", "开衫", "登山鞋", "短袖", "滑雪"]


async def test_products_filter_and_search(client):
    resp = await client.get("/api/v1/products", params={"cat": "滑雪"})
    data = resp.json()["data"]
    assert data["total"] == 4

    resp = await client.get("/api/v1/products", params={"q": "冲锋衣"})
    assert resp.json()["data"]["total"] == 1

    resp = await client.get("/api/v1/products", params={"cat": "开衫"})
    assert resp.json()["data"]["total"] == 0


async def test_products_sort_price(client):
    resp = await client.get("/api/v1/products", params={"sort": "price_desc"})
    prices = [p["price"] for p in resp.json()["data"]["items"]]
    assert prices == sorted(prices, reverse=True)
    assert prices[0] == 2399 * 100  # 单位为分


async def test_product_detail(client):
    listing = await client.get("/api/v1/products", params={"q": "冲锋衣"})
    spu_id = listing.json()["data"]["items"][0]["id"]

    resp = await client.get(f"/api/v1/products/{spu_id}")
    data = resp.json()["data"]
    assert data["en_model"] == "HYDROVA-M 1.0"
    assert len(data["colors"]) == 3
    assert data["sizes"] == ["XS", "S", "M", "L", "XL", "XXL"]
    assert len(data["skus"]) == 18  # 3 色 × 6 码
    assert all(s["stock"] == 100 for s in data["skus"])


async def test_product_not_found(client):
    resp = await client.get("/api/v1/products/99999")
    assert resp.status_code == 404
