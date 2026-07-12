from datetime import timedelta

from sqlalchemy import select

from app.db import SessionFactory
from app.models.order import Order
from app.services.orders import cancel_expired_orders
from app.utils import utcnow
from tests.conftest import login


async def _prepare(client, code: str) -> tuple[dict, dict, int]:
    """登录 + 建地址 + 取一个 SKU，返回 (headers, sku, address_id)。"""
    headers = await login(client, code)
    addr = await client.post("/api/v1/addresses", headers=headers, json={
        "name": "张三", "phone": "13800138000",
        "region": "浙江省 杭州市 西湖区", "detail": "文一西路 100 号",
    })
    addr_id = addr.json()["data"]["id"]

    listing = await client.get("/api/v1/products", params={"q": "连衣裙"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    detail = await client.get(f"/api/v1/products/{spu_id}")
    sku = detail.json()["data"]["skus"][0]
    return headers, sku, addr_id


async def _sku_stock(client, sku_id: int) -> int:
    listing = await client.get("/api/v1/products", params={"q": "连衣裙"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    detail = await client.get(f"/api/v1/products/{spu_id}")
    return next(s["stock"] for s in detail.json()["data"]["skus"] if s["id"] == sku_id)


async def test_preview(client):
    headers, sku, _ = await _prepare(client, "order-preview")
    resp = await client.post("/api/v1/orders/preview", headers=headers,
                             json={"items": [{"sku_id": sku["id"], "qty": 2}]})
    data = resp.json()["data"]
    assert data["item_amount"] == sku["price"] * 2
    assert data["pay_amount"] == sku["price"] * 2  # 运费 0
    assert data["items"][0]["qty"] == 2


async def test_order_full_flow(client):
    headers, sku, addr_id = await _prepare(client, "order-flow")
    stock_before = await _sku_stock(client, sku["id"])

    # 下单
    resp = await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 2}],
        "address_id": addr_id, "note": "尽快发货",
    })
    assert resp.status_code == 200, resp.text
    order = resp.json()["data"]
    assert order["status"] == "pending_payment"
    assert order["status_label"] == "待付款"
    assert order["pay_amount"] == sku["price"] * 2
    assert order["address"]["name"] == "张三"

    # 库存已扣
    assert await _sku_stock(client, sku["id"]) == stock_before - 2

    # 发起支付（mock）
    resp = await client.post(f"/api/v1/orders/{order['id']}/pay", headers=headers)
    assert resp.json()["data"]["provider"] == "mock"

    # 支付回调 → 待发货
    resp = await client.post("/api/v1/payments/mock/confirm",
                             json={"order_no": order["order_no"]})
    assert resp.json()["data"]["status"] == "pending_shipment"
    assert resp.json()["data"]["changed"] is True

    # 回调重放 → 幂等
    resp = await client.post("/api/v1/payments/mock/confirm",
                             json={"order_no": order["order_no"]})
    assert resp.json()["data"]["changed"] is False

    # 已支付订单不可取消
    resp = await client.post(f"/api/v1/orders/{order['id']}/cancel", headers=headers)
    assert resp.status_code == 400

    # 订单列表按状态过滤
    resp = await client.get("/api/v1/orders", headers=headers,
                            params={"status": "pending_shipment"})
    assert resp.json()["data"]["total"] == 1


async def test_cancel_restores_stock(client):
    headers, sku, addr_id = await _prepare(client, "order-cancel")
    stock_before = await _sku_stock(client, sku["id"])

    resp = await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 3}], "address_id": addr_id,
    })
    order = resp.json()["data"]
    assert await _sku_stock(client, sku["id"]) == stock_before - 3

    resp = await client.post(f"/api/v1/orders/{order['id']}/cancel", headers=headers)
    assert resp.json()["data"]["status"] == "cancelled"
    assert await _sku_stock(client, sku["id"]) == stock_before


async def test_insufficient_stock(client):
    headers, sku, addr_id = await _prepare(client, "order-oos")
    resp = await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 999}], "address_id": addr_id,
    })
    assert resp.status_code == 400
    assert "库存不足" in resp.json()["message"]


async def test_order_requires_own_address(client):
    headers, sku, _ = await _prepare(client, "order-addr-a")
    _, _, other_addr = await _prepare(client, "order-addr-b")
    resp = await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 1}], "address_id": other_addr,
    })
    assert resp.status_code == 400


async def test_expired_orders_cancelled(client):
    headers, sku, addr_id = await _prepare(client, "order-expire")
    stock_before = await _sku_stock(client, sku["id"])

    resp = await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 1}], "address_id": addr_id,
    })
    order_id = resp.json()["data"]["id"]

    # 把过期时间改到过去，模拟超时
    async with SessionFactory() as session:
        row = (await session.execute(select(Order).where(Order.id == order_id))).scalar_one()
        row.expire_at = utcnow() - timedelta(minutes=1)
        await session.commit()

    # 兜底扫描
    async with SessionFactory() as session:
        count = await cancel_expired_orders(session)
        await session.commit()
    assert count >= 1

    resp = await client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert resp.json()["data"]["status"] == "cancelled"
    assert await _sku_stock(client, sku["id"]) == stock_before
