async def test_stores(client):
    resp = await client.get("/api/v1/stores")
    assert resp.status_code == 200
    stores = resp.json()["data"]
    assert len(stores) == 3
    assert any(s["short_name"] == "北京三里屯" for s in stores)

    # 省市筛选
    resp = await client.get("/api/v1/stores", params={"province": "四川省"})
    assert resp.json()["data"][0]["city"] == "成都市"

    # 门店详情
    sid = stores[0]["id"]
    resp = await client.get(f"/api/v1/stores/{sid}")
    assert resp.json()["data"]["tel"]


async def test_store_regions(client):
    resp = await client.get("/api/v1/stores/regions")
    data = resp.json()["data"]
    assert "北京市" in data["provinces"]
    assert "成都市" in data["cities"]["四川省"]


async def test_pages_public_seed(client):
    """种子建了 home/brand 两个挂载页 + story 内容页；C 端可解析。"""
    data = (await client.get("/api/v1/pages/story")).json()["data"]
    assert data is not None and data["title"] == "品牌故事"
    assert any(b["kind"] == "text" for b in data["blocks"])
