from tests.conftest import login


async def _first_sku(client, q: str) -> dict:
    listing = await client.get("/api/v1/products", params={"q": q})
    spu_id = listing.json()["data"]["items"][0]["id"]
    detail = await client.get(f"/api/v1/products/{spu_id}")
    return detail.json()["data"]["skus"][0]


async def test_cart_flow(client):
    headers = await login(client, "cart-user")
    sku = await _first_sku(client, "手拿包")

    # 加购
    resp = await client.post("/api/v1/cart/items", headers=headers,
                             json={"sku_id": sku["id"], "qty": 1})
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["qty"] == 1

    # 同 SKU 再次加购 → 合并数量
    resp = await client.post("/api/v1/cart/items", headers=headers,
                             json={"sku_id": sku["id"], "qty": 2})
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["qty"] == 3

    # 修改数量
    item_id = items[0]["id"]
    resp = await client.patch(f"/api/v1/cart/items/{item_id}", headers=headers,
                              json={"qty": 5})
    assert resp.json()["data"][0]["qty"] == 5

    # 删除
    resp = await client.delete(f"/api/v1/cart/items/{item_id}", headers=headers)
    assert resp.json()["data"] == []


async def test_cart_isolated_between_users(client):
    h1 = await login(client, "cart-a")
    h2 = await login(client, "cart-b")
    sku = await _first_sku(client, "项链")

    await client.post("/api/v1/cart/items", headers=h1, json={"sku_id": sku["id"], "qty": 1})
    resp = await client.get("/api/v1/cart", headers=h2)
    assert resp.json()["data"] == []


async def test_cart_invalid_sku(client):
    headers = await login(client, "cart-invalid")
    resp = await client.post("/api/v1/cart/items", headers=headers,
                             json={"sku_id": 999999, "qty": 1})
    assert resp.status_code == 404
