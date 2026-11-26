"""整单退款：管理端直接退，顾客不能申请。mock 不访问微信。"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionFactory
from app.models.catalog import Sku, Spu
from app.models.order import Order, OrderStatus, Payment, Refund
from app.utils import utcnow
from tests.conftest import login
from tests.test_admin import admin_login


async def _paid_order(client, code: str, *, use_points: bool = False, user_coupon_id: int | None = None):
    headers = await login(client, code)
    addr = await client.post("/api/v1/addresses", headers=headers, json={
        "name": "退款测试", "phone": "13800138000",
        "region": "浙江省 杭州市 西湖区", "detail": "文一西路 100 号",
    })
    listing = await client.get("/api/v1/products", params={"q": "连衣裙"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    detail = await client.get(f"/api/v1/products/{spu_id}")
    sku = detail.json()["data"]["skus"][0]
    body = {
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr.json()["data"]["id"],
        "use_points": use_points,
    }
    if user_coupon_id:
        body["user_coupon_id"] = user_coupon_id
    resp = await client.post("/api/v1/orders", headers=headers, json=body)
    assert resp.status_code == 200, resp.text
    order = resp.json()["data"]
    paid = await client.post("/api/v1/payments/mock/confirm", json={"order_no": order["order_no"]})
    assert paid.json()["data"]["status"] == "pending_shipment"
    return headers, order, sku


async def _levels(sku_id: int) -> tuple[int, int]:
    async with SessionFactory() as session:
        sku = await session.get(Sku, sku_id)
        spu = await session.get(Spu, sku.spu_id)
        return sku.stock, spu.sales


async def _set_shipped_at(order_id: int, when) -> None:
    async with SessionFactory() as session:
        order = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one()
        order.shipped_at = when
        await session.commit()


async def _seed_refund(order: dict, status: str) -> None:
    async with SessionFactory() as session:
        row = (await session.execute(select(Order).where(Order.id == order["id"]))).scalar_one()
        row.status = OrderStatus.REFUND_PENDING
        session.add(Refund(
            order_id=row.id,
            out_refund_no="R" + row.order_no,
            reason="客服确认退款",
            status=status,
            previous_status=OrderStatus.PENDING_SHIPMENT,
            amount=row.pay_amount,
        ))
        await session.commit()


async def test_admin_refund_restores_stock_sales_coupon_and_payment(client):
    admin_h = await admin_login(client)
    coupon = (await client.post("/api/admin/coupons", headers=admin_h, json={
        "name": "退款退券", "threshold": 0, "amount": 100,
        "total": 0, "per_user_limit": 1, "valid_days": 7, "status": 1,
    })).json()["data"]
    headers, _, sku = await _paid_order(client, "refund-stock")
    claimed = (await client.post(f"/api/v1/coupons/{coupon['id']}/claim", headers=headers)).json()["data"]
    addr = (await client.get("/api/v1/addresses", headers=headers)).json()["data"][0]
    order = (await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr["id"],
        "user_coupon_id": claimed["id"],
    })).json()["data"]
    await client.post("/api/v1/payments/mock/confirm", json={"order_no": order["order_no"]})

    unpaid = (await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 1}], "address_id": addr["id"],
    })).json()["data"]
    resp = await client.post(f"/api/admin/orders/{unpaid['id']}/refund", headers=admin_h, json={})
    assert resp.status_code == 400
    assert resp.json()["message"] == "当前状态不可退款"
    resp = await client.post(f"/api/v1/orders/{unpaid['order_no']}/refund", headers=headers, json={})
    assert resp.status_code == 404
    await client.post(f"/api/v1/orders/{unpaid['order_no']}/cancel", headers=headers)
    stock_after_pay, sales_after_pay = await _levels(sku["id"])

    detail = (await client.get(f"/api/v1/orders/{order['order_no']}", headers=headers)).json()["data"]
    assert detail["can_refund"] is False
    resp = await client.post(f"/api/admin/orders/{order['id']}/refund", headers=headers, json={})
    assert resp.status_code == 401
    other = await login(client, "refund-other")
    resp = await client.get(f"/api/v1/orders/{order['order_no']}", headers=other)
    assert resp.status_code == 404

    resp = await client.post(f"/api/admin/orders/{order['id']}/refund", headers=admin_h, json={})
    assert resp.status_code == 200, resp.text
    done = resp.json()["data"]
    assert done["status"] == "refunded"
    assert done["status_label"] == "已退款"
    assert done["can_refund"] is False
    assert done["refund"]["status"] == "success"
    assert done["refund"]["reason"] == "客服确认退款"
    assert (await _levels(sku["id"])) == (stock_after_pay + 1, sales_after_pay - 1)

    async with SessionFactory() as session:
        pays = (await session.execute(select(Payment).where(Payment.order_id == order["id"]))).scalars().all()
    assert [p.status for p in pays] == ["refunded"]
    mine = (await client.get("/api/v1/me/coupons", headers=headers)).json()["data"]
    assert next(row for row in mine if row["id"] == claimed["id"])["status"] == "unused"

    listed = (await client.get("/api/v1/orders", headers=headers, params={"status": "after_sale"})).json()["data"]
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == order["id"]
    resp = await client.get("/api/v1/orders", headers=headers, params={"status": "not_a_status"})
    assert resp.status_code == 400

    again = await client.post(f"/api/admin/orders/{order['id']}/refund", headers=admin_h, json={})
    assert again.status_code == 400
    assert (await _levels(sku["id"])) == (stock_after_pay + 1, sales_after_pay - 1)


async def test_admin_can_refund_shipped_order_after_eight_days(client):
    admin_h = await admin_login(client)
    headers, order, sku = await _paid_order(client, "refund-window")
    stock_paid, sales_paid = await _levels(sku["id"])
    resp = await client.post(
        f"/api/admin/orders/{order['id']}/ship", headers=admin_h,
        json={"company": "顺丰", "tracking_no": "SF700000"},
    )
    assert resp.json()["data"]["status"] == "pending_receipt"
    await _set_shipped_at(order["id"], utcnow() - timedelta(days=8))

    detail = (await client.get(f"/api/v1/orders/{order['order_no']}", headers=headers)).json()["data"]
    assert detail["can_refund"] is False
    resp = await client.post(f"/api/v1/orders/{order['order_no']}/refund", headers=headers, json={})
    assert resp.status_code == 404

    resp = await client.post(
        f"/api/admin/orders/{order['id']}/refund", headers=admin_h, json={"reason": "查验完好"},
    )
    assert resp.status_code == 200, resp.text
    done = resp.json()["data"]
    assert done["status"] == "refunded"
    assert done["refund"]["reason"] == "查验完好"
    assert (await _levels(sku["id"])) == (stock_paid + 1, sales_paid - 1)


async def test_admin_refunds_completed_order(client):
    admin_h = await admin_login(client)
    headers, order, _ = await _paid_order(client, "refund-done")
    await client.post(
        f"/api/admin/orders/{order['id']}/ship", headers=admin_h,
        json={"company": "顺丰", "tracking_no": "SF700111"},
    )
    await client.post(f"/api/v1/orders/{order['order_no']}/confirm", headers=headers)
    resp = await client.post(f"/api/admin/orders/{order['id']}/refund", headers=admin_h, json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "refunded"


async def test_failed_retry_uses_same_number_and_processing_is_blocked(client):
    admin_h = await admin_login(client)
    headers, failed, sku = await _paid_order(client, "refund-retry")
    stock_paid, sales_paid = await _levels(sku["id"])
    await _seed_refund(failed, "failed")
    resp = await client.post(f"/api/admin/orders/{failed['id']}/refund", headers=admin_h, json={})
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "refunded"
    assert (await _levels(sku["id"])) == (stock_paid + 1, sales_paid - 1)
    async with SessionFactory() as session:
        saved = (await session.execute(
            select(Order).options(selectinload(Order.refunds)).where(Order.id == failed["id"])
        )).scalar_one()
        numbers = [row.out_refund_no for row in saved.refunds]
        statuses = [row.status for row in saved.refunds]
    assert numbers == ["R" + failed["order_no"]]
    assert statuses == ["success"]

    headers2, processing, sku2 = await _paid_order(client, "refund-processing")
    held = await _levels(sku2["id"])
    await _seed_refund(processing, "processing")
    resp = await client.post(f"/api/admin/orders/{processing['id']}/refund", headers=admin_h, json={})
    assert resp.status_code == 400
    assert resp.json()["message"] == "退款处理中"
    assert (await _levels(sku2["id"])) == held
    detail = (await client.get(f"/api/v1/orders/{processing['order_no']}", headers=headers2)).json()["data"]
    assert detail["status"] == "refund_pending"
    assert detail["refund"]["status"] == "processing"


async def test_refund_returns_points_and_shortfall_does_not_block(client):
    admin_h = await admin_login(client)
    headers = await login(client, "refund-points")
    addr = (await client.post("/api/v1/addresses", headers=headers, json={
        "name": "积分退款", "phone": "13800138000", "region": "", "detail": "路 1 号",
    })).json()["data"]
    me = (await client.get("/api/v1/me", headers=headers)).json()["data"]
    await client.post(f"/api/admin/users/{me['id']}/points", headers=admin_h,
                      json={"change": 500, "remark": "退款测试"})
    listing = await client.get("/api/v1/products", params={"q": "连衣裙"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    sku = (await client.get(f"/api/v1/products/{spu_id}")).json()["data"]["skus"][0]
    spent = (await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr["id"],
        "use_points": True,
    })).json()["data"]
    assert spent["points_used"] == 500
    assert spent["pay_amount"] // 100 > spent["points_used"]
    await client.post("/api/v1/payments/mock/confirm", json={"order_no": spent["order_no"]})
    approved = await client.post(f"/api/admin/orders/{spent['id']}/refund", headers=admin_h, json={})
    assert approved.status_code == 200, approved.text
    assert (await client.get("/api/v1/me", headers=headers)).json()["data"]["points"] == 500

    await client.post(f"/api/admin/users/{me['id']}/points", headers=admin_h,
                      json={"change": 500, "remark": "再测一次"})
    spent = (await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr["id"],
        "use_points": True,
    })).json()["data"]
    assert spent["pay_amount"] // 100 > spent["points_used"]
    await client.post("/api/v1/payments/mock/confirm", json={"order_no": spent["order_no"]})
    balance = (await client.get("/api/v1/me", headers=headers)).json()["data"]["points"]
    await client.post(f"/api/admin/users/{me['id']}/points", headers=admin_h,
                      json={"change": -balance, "remark": "花光奖励"})
    assert (await client.get("/api/v1/me", headers=headers)).json()["data"]["points"] == 0
    approved = await client.post(f"/api/admin/orders/{spent['id']}/refund", headers=admin_h, json={})
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["status"] == "refunded"
    assert (await client.get("/api/v1/me", headers=headers)).json()["data"]["points"] == spent["points_used"]
    logs = (await client.get("/api/v1/me/points/logs", headers=headers)).json()["data"]
    assert any(row["change"] == spent["points_used"] and row["reason"] == "订单退回" for row in logs)
