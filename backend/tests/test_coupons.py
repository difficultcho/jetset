from datetime import timedelta

from sqlalchemy import select

from app.db import SessionFactory
from app.models.coupon import UserCoupon
from app.utils import utcnow
from tests.conftest import login
from tests.test_admin import admin_login


async def _create_coupon(client, admin_h, **kw):
    payload = {
        "name": "满100减20", "threshold": 10000, "amount": 2000,
        "total": 0, "per_user_limit": 1, "valid_days": 7, "status": 1,
    }
    payload.update(kw)
    resp = await client.post("/api/admin/coupons", headers=admin_h, json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _prepare_user(client, code):
    """登录 + 建地址 + 找一个高价 SKU（滑雪镜 ¥398）。"""
    h = await login(client, code)
    addr = await client.post("/api/v1/addresses", headers=h, json={
        "name": "券测试", "phone": "13700000000", "region": "", "detail": "路 9 号"})
    listing = await client.get("/api/v1/products", params={"q": "滑雪镜"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    sku = (await client.get(f"/api/v1/products/{spu_id}")).json()["data"]["skus"][0]
    return h, sku, addr.json()["data"]["id"]


async def test_claim_and_center(client):
    admin_h = await admin_login(client)
    c = await _create_coupon(client, admin_h, name="领取测试券", total=2, per_user_limit=1)
    h = await login(client, "cp-claim")

    center = (await client.get("/api/v1/coupons/center", headers=h)).json()["data"]
    row = next(x for x in center if x["id"] == c["id"])
    assert row["claimable"] is True

    resp = await client.post(f"/api/v1/coupons/{c['id']}/claim", headers=h)
    assert resp.json()["data"]["status"] == "unused"

    # 每人限领 1 张，重复领取被拒
    resp = await client.post(f"/api/v1/coupons/{c['id']}/claim", headers=h)
    assert resp.status_code == 400

    # 第二个人领掉最后一张，第三个人领取时已领完
    h2 = await login(client, "cp-claim2")
    assert (await client.post(f"/api/v1/coupons/{c['id']}/claim", headers=h2)).status_code == 200
    h3 = await login(client, "cp-claim3")
    resp = await client.post(f"/api/v1/coupons/{c['id']}/claim", headers=h3)
    assert resp.status_code == 400
    assert "领完" in resp.json()["message"]

    # 我的券列表
    mine = (await client.get("/api/v1/me/coupons", headers=h)).json()["data"]
    assert len([x for x in mine if x["status"] == "unused"]) >= 1


async def test_preview_and_order_with_coupon(client):
    admin_h = await admin_login(client)
    c = await _create_coupon(client, admin_h, name="下单券", threshold=10000, amount=2000)
    h, sku, addr_id = await _prepare_user(client, "cp-order")
    uc = (await client.post(f"/api/v1/coupons/{c['id']}/claim", headers=h)).json()["data"]

    # 试算：1 件 ¥398 满足 ¥100 门槛
    resp = await client.post("/api/v1/orders/preview", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}], "user_coupon_id": uc["id"]})
    data = resp.json()["data"]
    assert data["discount_amount"] == 2000
    assert data["pay_amount"] == sku["price"] - 2000
    assert data["applied_coupon_id"] == uc["id"]
    assert any(x["id"] == uc["id"] and x["usable"] for x in data["coupons"])

    # 下单用券
    resp = await client.post("/api/v1/orders", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr_id, "user_coupon_id": uc["id"]})
    order = resp.json()["data"]
    assert order["discount_amount"] == 2000
    assert order["pay_amount"] == sku["price"] - 2000

    # 券已用，不能再用于下单
    mine = (await client.get("/api/v1/me/coupons", headers=h)).json()["data"]
    assert next(x for x in mine if x["id"] == uc["id"])["status"] == "used"
    resp = await client.post("/api/v1/orders", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr_id, "user_coupon_id": uc["id"]})
    assert resp.status_code == 400


async def test_threshold_not_met(client):
    admin_h = await admin_login(client)
    c = await _create_coupon(client, admin_h, name="高门槛券", threshold=99999900, amount=2000)
    h, sku, addr_id = await _prepare_user(client, "cp-threshold")
    uc = (await client.post(f"/api/v1/coupons/{c['id']}/claim", headers=h)).json()["data"]

    resp = await client.post("/api/v1/orders/preview", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}], "user_coupon_id": uc["id"]})
    assert resp.status_code == 400
    assert "门槛" in resp.json()["message"]

    # 不指定券时，列表标记 usable=False
    resp = await client.post("/api/v1/orders/preview", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}]})
    row = next(x for x in resp.json()["data"]["coupons"] if x["id"] == uc["id"])
    assert row["usable"] is False


async def test_cancel_order_releases_coupon(client):
    admin_h = await admin_login(client)
    c = await _create_coupon(client, admin_h, name="退券测试")
    h, sku, addr_id = await _prepare_user(client, "cp-release")
    uc = (await client.post(f"/api/v1/coupons/{c['id']}/claim", headers=h)).json()["data"]

    order = (await client.post("/api/v1/orders", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr_id, "user_coupon_id": uc["id"]})).json()["data"]

    await client.post(f"/api/v1/orders/{order['id']}/cancel", headers=h)

    mine = (await client.get("/api/v1/me/coupons", headers=h)).json()["data"]
    assert next(x for x in mine if x["id"] == uc["id"])["status"] == "unused"


async def test_expired_coupon_unusable(client):
    admin_h = await admin_login(client)
    c = await _create_coupon(client, admin_h, name="过期测试券")
    h, sku, addr_id = await _prepare_user(client, "cp-expired")
    uc = (await client.post(f"/api/v1/coupons/{c['id']}/claim", headers=h)).json()["data"]

    # 直接把过期时间改到过去
    async with SessionFactory() as session:
        row = (await session.execute(select(UserCoupon).where(UserCoupon.id == uc["id"]))).scalar_one()
        row.expires_at = utcnow() - timedelta(minutes=1)
        await session.commit()

    mine = (await client.get("/api/v1/me/coupons", headers=h, params={"status": "expired"})).json()["data"]
    assert any(x["id"] == uc["id"] for x in mine)

    resp = await client.post("/api/v1/orders", headers=h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr_id, "user_coupon_id": uc["id"]})
    assert resp.status_code == 400


async def test_admin_coupon_validation(client):
    admin_h = await admin_login(client)
    # 有效期必须至少配一种
    resp = await client.post("/api/admin/coupons", headers=admin_h, json={
        "name": "无有效期", "threshold": 0, "amount": 100})
    assert resp.status_code == 422
    # 减免不能 >= 门槛
    resp = await client.post("/api/admin/coupons", headers=admin_h, json={
        "name": "倒挂券", "threshold": 100, "amount": 200, "valid_days": 7})
    assert resp.status_code == 422

    # 下架后领券中心不可见
    c = await _create_coupon(client, admin_h, name="下架测试券")
    await client.post(f"/api/admin/coupons/{c['id']}/status", headers=admin_h, json={"status": 0})
    h = await login(client, "cp-off")
    center = (await client.get("/api/v1/coupons/center", headers=h)).json()["data"]
    assert not any(x["id"] == c["id"] for x in center)

    # 管理端列表含统计字段
    rows = (await client.get("/api/admin/coupons", headers=admin_h)).json()["data"]
    assert all("taken" in r and "used" in r for r in rows)
