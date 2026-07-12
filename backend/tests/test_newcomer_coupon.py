from tests.conftest import login
from tests.test_admin import admin_login


async def _create_newcomer_coupon(client, admin_h, **kw):
    payload = {
        "name": "新人无门槛减10", "threshold": 0, "amount": 1000,
        "total": 0, "per_user_limit": 1, "valid_days": 30,
        "is_newcomer": True, "status": 1,
    }
    payload.update(kw)
    resp = await client.post("/api/admin/coupons", headers=admin_h, json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def test_newcomer_gets_coupon_on_register(client):
    admin_h = await admin_login(client)
    c = await _create_newcomer_coupon(client, admin_h)

    # 新用户首次登录 → 自动发券，响应携带数量
    resp = await client.post("/api/v1/auth/login", json={"code": "newcomer-a"})
    data = resp.json()["data"]
    assert data["new_coupons"] >= 1
    h = {"Authorization": "Bearer " + data["token"]}

    mine = (await client.get("/api/v1/me/coupons", headers=h)).json()["data"]
    assert any(x["name"] == "新人无门槛减10" and x["status"] == "unused" for x in mine)

    # 同一用户再次登录（老用户）→ 不重复发
    resp = await client.post("/api/v1/auth/login", json={"code": "newcomer-a"})
    assert resp.json()["data"]["new_coupons"] == 0
    mine2 = (await client.get("/api/v1/me/coupons", headers=h)).json()["data"]
    assert len(mine2) == len(mine)


async def test_newcomer_coupon_hidden_and_unclaimable(client):
    admin_h = await admin_login(client)
    c = await _create_newcomer_coupon(client, admin_h, name="隐藏新客券")

    h = await login(client, "newcomer-b")
    center = (await client.get("/api/v1/coupons/center", headers=h)).json()["data"]
    assert not any(x["id"] == c["id"] for x in center)

    resp = await client.post(f"/api/v1/coupons/{c['id']}/claim", headers=h)
    assert resp.status_code == 400
    assert "新人专享" in resp.json()["message"]


async def test_soldout_newcomer_coupon_does_not_block_register(client):
    admin_h = await admin_login(client)
    # 发行量 1，先让一个新用户领走
    await _create_newcomer_coupon(client, admin_h, name="限量新客券", total=1)
    r1 = await client.post("/api/v1/auth/login", json={"code": "newcomer-c1"})
    assert r1.status_code == 200

    # 下一个新用户注册不因券领完而失败
    r2 = await client.post("/api/v1/auth/login", json={"code": "newcomer-c2"})
    assert r2.status_code == 200
    h2 = {"Authorization": "Bearer " + r2.json()["data"]["token"]}
    mine = (await client.get("/api/v1/me/coupons", headers=h2)).json()["data"]
    assert not any(x["name"] == "限量新客券" for x in mine)


async def test_newcomer_coupon_usable_in_order(client):
    admin_h = await admin_login(client)
    await _create_newcomer_coupon(client, admin_h, name="新人下单券", threshold=0, amount=1000)

    resp = await client.post("/api/v1/auth/login", json={"code": "newcomer-d"})
    h = {"Authorization": "Bearer " + resp.json()["data"]["token"]}

    addr = await client.post("/api/v1/addresses", headers=h, json={
        "name": "新客", "phone": "13400000000", "region": "", "detail": "路 6 号"})
    listing = await client.get("/api/v1/products", params={"q": "单肩包"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    sku = (await client.get(f"/api/v1/products/{spu_id}")).json()["data"]["skus"][0]

    # preview 不带券时也会列出可用新客券
    pv = (await client.post("/api/v1/orders/preview", headers=h,
                            json={"items": [{"sku_id": sku["id"], "qty": 1}]})).json()["data"]
    uc = next(x for x in pv["coupons"] if x["name"] == "新人下单券")
    assert uc["usable"] is True

    order = (await client.post("/api/v1/orders", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr.json()["data"]["id"],
        "user_coupon_id": uc["id"]})).json()["data"]
    assert order["discount_amount"] == 1000
