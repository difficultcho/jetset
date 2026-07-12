from tests.conftest import login
from tests.test_admin import admin_login


async def _prepare(client, code, q="连衣裙"):
    h = await login(client, code)
    addr = await client.post("/api/v1/addresses", headers=h, json={
        "name": "积分测试", "phone": "13300000000", "region": "", "detail": "路 5 号"})
    listing = await client.get("/api/v1/products", params={"q": q})
    spu_id = listing.json()["data"]["items"][0]["id"]
    sku = (await client.get(f"/api/v1/products/{spu_id}")).json()["data"]["skus"][0]
    return h, sku, addr.json()["data"]["id"]


async def _my_points(client, h) -> int:
    return (await client.get("/api/v1/me", headers=h)).json()["data"]["points"]


async def _adjust(client, admin_h, user_id, change, remark="测试调整"):
    return await client.post(f"/api/admin/users/{user_id}/points", headers=admin_h,
                             json={"change": change, "remark": remark})


async def _uid(client, h) -> int:
    return (await client.get("/api/v1/me", headers=h)).json()["data"]["id"]


async def test_pay_rewards_points(client):
    h, sku, addr_id = await _prepare(client, "pt-reward")
    order = (await client.post("/api/v1/orders", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}], "address_id": addr_id})).json()["data"]

    assert await _my_points(client, h) == 0
    await client.post("/api/v1/payments/mock/confirm", json={"order_no": order["order_no"]})

    expect = order["pay_amount"] // 100  # 实付 1 元 = 1 积分
    assert await _my_points(client, h) == expect

    # 回调重放不重复发
    await client.post("/api/v1/payments/mock/confirm", json={"order_no": order["order_no"]})
    assert await _my_points(client, h) == expect

    logs = (await client.get("/api/v1/me/points/logs", headers=h)).json()["data"]
    assert logs[0]["reason"] == "购物奖励" and logs[0]["change"] == expect
    assert logs[0]["balance_after"] == expect


async def test_points_deduct_and_refund(client):
    admin_h = await admin_login(client)
    h, sku, addr_id = await _prepare(client, "pt-deduct")
    await _adjust(client, admin_h, await _uid(client, h), 5000)

    # 试算：5000 积分全额可用（100 积分 = ¥1 → 抵 5000 分）
    pv = (await client.post("/api/v1/orders/preview", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}], "use_points": True})).json()["data"]
    assert pv["points_available"] == 5000
    assert pv["points_used"] == 5000
    assert pv["points_deduct"] == 5000
    assert pv["pay_amount"] == pv["item_amount"] - 5000

    # 下单：积分扣除
    order = (await client.post("/api/v1/orders", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr_id, "use_points": True})).json()["data"]
    assert order["points_used"] == 5000
    assert await _my_points(client, h) == 0

    # 取消：积分退回
    await client.post(f"/api/v1/orders/{order['id']}/cancel", headers=h)
    assert await _my_points(client, h) == 5000
    logs = (await client.get("/api/v1/me/points/logs", headers=h)).json()["data"]
    assert logs[0]["reason"] == "订单退回"


async def test_points_capped_by_order_amount(client):
    admin_h = await admin_login(client)
    h, sku, addr_id = await _prepare(client, "pt-cap", q="项链")
    await _adjust(client, admin_h, await _uid(client, h), 999999)

    pv = (await client.post("/api/v1/orders/preview", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}], "use_points": True})).json()["data"]
    # 抵扣不超过商品总额，应付为运费（0）
    assert pv["points_deduct"] == pv["item_amount"]
    assert pv["pay_amount"] == 0

    order = (await client.post("/api/v1/orders", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr_id, "use_points": True})).json()["data"]
    assert order["pay_amount"] == 0
    assert await _my_points(client, h) == 999999 - order["points_used"]


async def test_coupon_and_points_stack(client):
    admin_h = await admin_login(client)
    # 无门槛减 20 的券
    c = (await client.post("/api/admin/coupons", headers=admin_h, json={
        "name": "叠加测试券", "threshold": 0, "amount": 2000, "valid_days": 7})).json()["data"]
    h, sku, addr_id = await _prepare(client, "pt-stack")
    uc = (await client.post(f"/api/v1/coupons/{c['id']}/claim", headers=h)).json()["data"]
    await _adjust(client, admin_h, await _uid(client, h), 3000)

    pv = (await client.post("/api/v1/orders/preview", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "user_coupon_id": uc["id"], "use_points": True})).json()["data"]
    # 顺序：商品总额 → 券 → 积分
    assert pv["discount_amount"] == 2000
    assert pv["points_deduct"] == 3000
    assert pv["pay_amount"] == pv["item_amount"] - 2000 - 3000


async def test_admin_adjust_validation(client):
    admin_h = await admin_login(client)
    h = await login(client, "pt-admin")
    uid = await _uid(client, h)

    assert (await _adjust(client, admin_h, uid, 100)).json()["data"]["points"] == 100
    assert (await _adjust(client, admin_h, uid, -40)).json()["data"]["points"] == 60
    # 扣超余额被拒
    resp = await _adjust(client, admin_h, uid, -999)
    assert resp.status_code == 400
    # 0 被 schema 拒绝
    resp = await client.post(f"/api/admin/users/{uid}/points", headers=admin_h,
                             json={"change": 0, "remark": "x"})
    assert resp.status_code == 422

    logs = (await client.get("/api/v1/me/points/logs", headers=h)).json()["data"]
    assert logs[0]["reason"] == "平台调整" and logs[0]["balance_after"] == 60
