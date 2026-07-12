from app.services import wechat
from tests.conftest import login


async def test_risky_nickname_rejected(client, monkeypatch):
    async def fake_check(openid, content):
        return "risky" if "违规词" in content else "pass"

    monkeypatch.setattr(wechat, "msg_sec_check", fake_check)

    headers = await login(client, "sec-user")
    resp = await client.put("/api/v1/me", headers=headers, json={"name": "含违规词的昵称"})
    assert resp.status_code == 400
    assert "违规" in resp.json()["message"]

    resp = await client.put("/api/v1/me", headers=headers, json={"name": "正常昵称"})
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "正常昵称"


async def test_risky_order_note_rejected(client, monkeypatch):
    async def fake_check(openid, content):
        return "risky"

    monkeypatch.setattr(wechat, "msg_sec_check", fake_check)

    headers = await login(client, "sec-note")
    addr = await client.post("/api/v1/addresses", headers=headers, json={
        "name": "安审", "phone": "13500000000", "region": "", "detail": "路 7 号"})
    listing = await client.get("/api/v1/products", params={"q": "项链"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    sku = (await client.get(f"/api/v1/products/{spu_id}")).json()["data"]["skus"][0]

    resp = await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr.json()["data"]["id"], "note": "任何备注"})
    assert resp.status_code == 400

    # 无备注不触发检测，正常下单
    resp = await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr.json()["data"]["id"]})
    assert resp.status_code == 200


async def test_mock_mode_skips_check(client):
    # 测试环境 WECHAT_MOCK=true：真实实现直接放行，不请求微信
    assert await wechat.msg_sec_check("any-openid", "任何内容") == "pass"
