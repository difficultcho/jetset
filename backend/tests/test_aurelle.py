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


async def test_brand_projects(client):
    resp = await client.get("/api/v1/brand/posts", params={"type": "project"})
    posts = resp.json()["data"]
    assert len(posts) == 6
    assert all(p["type"] == "project" for p in posts)


async def test_brand_story_and_moment(client):
    for t in ("story", "moment", "campaign"):
        resp = await client.get("/api/v1/brand/first", params={"type": t})
        assert resp.status_code == 200
        d = resp.json()["data"]
        assert d is not None
        assert isinstance(d["body"], list) and len(d["body"]) > 0
