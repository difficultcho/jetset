async def test_home(client):
    resp = await client.get("/api/v1/home")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["hot"]) == 5          # 13 商品，hot 取前 5
    assert len(data["grid"]) == 10        # grid 从第 4 个开始
    assert data["featured"] is not None   # 前 3 个 featured


async def test_categories_tree(client):
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    tops = resp.json()["data"]
    names = [c["name"] for c in tops]
    assert names == ["连衣裙", "上衣", "鞋履", "包袋", "珠宝", "配饰", "童装"]
    # 鞋履含二级品类
    shoes = next(c for c in tops if c["name"] == "鞋履")
    sub = [s["name"] for s in shoes["children"]]
    assert "穆勒鞋" in sub and "凉鞋" in sub


async def test_series(client):
    resp = await client.get("/api/v1/series")
    assert resp.status_code == 200
    ens = [s["en"] for s in resp.json()["data"]]
    assert "HIGH SUMMER" in ens and "CRUISE 2027" in ens


async def test_products_filter_by_category_subtree(client):
    # 一级品类「鞋履」应含全部二级（穆勒鞋/凉鞋）下的商品 = 4 件
    resp = await client.get("/api/v1/products", params={"cat": "鞋履"})
    assert resp.json()["data"]["total"] == 4
    # 二级品类「凉鞋」= 2 件
    resp = await client.get("/api/v1/products", params={"cat": "凉鞋"})
    assert resp.json()["data"]["total"] == 2
    # 连衣裙 = 4 件
    resp = await client.get("/api/v1/products", params={"cat": "连衣裙"})
    assert resp.json()["data"]["total"] == 4


async def test_products_filter_by_series(client):
    series = (await client.get("/api/v1/series")).json()["data"]
    hs = next(s for s in series if s["en"] == "HIGH SUMMER")
    resp = await client.get("/api/v1/products", params={"series": hs["id"]})
    assert resp.json()["data"]["total"] == 10  # HIGH SUMMER 系列 10 件


async def test_products_search(client):
    resp = await client.get("/api/v1/products", params={"q": "斗篷"})
    assert resp.json()["data"]["total"] == 1


async def test_products_sort_price(client):
    resp = await client.get("/api/v1/products", params={"sort": "price_desc"})
    prices = [p["price"] for p in resp.json()["data"]["items"]]
    assert prices == sorted(prices, reverse=True)
    assert prices[0] == 21750 * 100  # 丝巾拼接连衣裙最高价（分）


async def test_product_detail(client):
    listing = await client.get("/api/v1/products", params={"q": "挂脖牛仔连衣裙"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    resp = await client.get(f"/api/v1/products/{spu_id}")
    data = resp.json()["data"]
    assert data["code"] == "AU433DSS266"
    assert data["sub"] == "挂脖牛仔连衣裙"
    assert data["has_video"] is True
    assert len(data["bullets"]) > 0
    assert data["series"]["en"] == "HIGH SUMMER"
    assert data["sizes"] == ["0", "1", "2", "3"]
    assert len(data["skus"]) == 4  # 1 色 × 4 码


async def test_product_sale_original_price(client):
    listing = await client.get("/api/v1/products", params={"q": "花朵造型"})
    item = listing.json()["data"]["items"][0]
    assert item["original_price"] == 7350 * 100
    assert item["price"] == 3675 * 100


async def test_product_not_found(client):
    resp = await client.get("/api/v1/products/99999")
    assert resp.status_code == 404
