async def test_stores(client):
    resp = await client.get("/api/v1/stores")
    assert resp.status_code == 200
    stores = resp.json()["data"]
    assert len(stores) == 6                      # 国内 3 + 海外 3
    assert any(s["short_name"] == "北京三里屯" for s in stores)
    assert any(s["country"] == "瑞士" for s in stores)

    # 国家/城市筛选（第一级是国家，不是省份）
    resp = await client.get("/api/v1/stores", params={"country": "瑞士"})
    assert {s["city"] for s in resp.json()["data"]} == {"St. Moritz", "Verbier"}
    resp = await client.get("/api/v1/stores", params={"city": "Courchevel"})
    assert resp.json()["data"][0]["country"] == "法国"

    # 门店详情
    sid = stores[0]["id"]
    resp = await client.get(f"/api/v1/stores/{sid}")
    assert resp.json()["data"]["tel"]


async def test_store_regions(client):
    """下拉数据源：国家去重后按门店 sort 排序，城市按国家分组。"""
    resp = await client.get("/api/v1/stores/regions")
    data = resp.json()["data"]
    assert data["countries"][0] == "中国"        # sort 最小的门店在国内 → 中国排最前
    assert set(data["countries"]) == {"中国", "瑞士", "法国"}
    assert data["cities"]["瑞士"] == ["St. Moritz", "Verbier"]
    assert "成都市" in data["cities"]["中国"]


async def test_pages_public_seed(client):
    """种子建了 home/brand 两个挂载页 + story 内容页；C 端可解析。"""
    data = (await client.get("/api/v1/pages/story")).json()["data"]
    assert data is not None and data["title"] == "品牌故事"
    assert any(b["kind"] == "text" for b in data["blocks"])
