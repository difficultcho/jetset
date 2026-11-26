"""发货信息录入。不访问微信。mock 发货不组包；正式环境失败时订单保持待发货。"""

import json
from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select

from app.config import settings
from app.db import SessionFactory
from app.errors import BizError
from app.models.order import Order, Payment
from app.models.user import User
from app.services import shipping
from tests.conftest import login
from tests.test_admin import admin_login


def test_payload_uses_transaction_masks_sf_phone_and_clips_desc():
    when = datetime(2022, 12, 15, 5, 29, 35, 120000)
    phone = "+86 138-0013-8000"
    payload = shipping.build_payload(
        order_no="202611241200000001",
        transaction_id="4200000000000001",
        mchid="1900000001",
        openid="o_payer",
        delivery_id="SF",
        tracking_no="SF1234567890",
        description=shipping.item_desc([
            SimpleNamespace(name="衣" * 130, qty=2),
            SimpleNamespace(name="裤", qty=1),
        ]),
        phone=phone,
        when=when,
    )
    assert payload["order_key"] == {"order_number_type": 2, "transaction_id": "4200000000000001"}
    assert payload["logistics_type"] == 1
    assert payload["delivery_mode"] == 1
    assert payload["upload_time"] == "2022-12-15T05:29:35.120+00:00"
    assert payload["payer"] == {"openid": "o_payer"}
    item = payload["shipping_list"][0]
    assert item["express_company"] == "SF"
    assert item["tracking_no"] == "SF1234567890"
    assert item["contact"] == {"receiver_contact": "138****8000"}
    assert len(item["item_desc"]) == 120
    dumped = json.dumps(payload, ensure_ascii=False)
    assert "13800138000" not in dumped
    assert "138-0013-8000" not in dumped

    plain = shipping.build_payload(
        order_no="202611241200000001",
        transaction_id="",
        mchid="1900000001",
        openid="o_payer",
        delivery_id="YTO",
        tracking_no="YT1",
        description="裤子*1",
        phone=phone,
        when=when,
    )
    assert plain["order_key"] == {
        "order_number_type": 1,
        "mchid": "1900000001",
        "out_trade_no": "202611241200000001",
    }
    assert "contact" not in plain["shipping_list"][0]
    assert shipping.mask_phone("18912341234") == "189****1234"
    assert shipping.mask_phone("12345") is None
    with pytest.raises(BizError) as raised:
        shipping.build_payload(
            order_no="202611241200000001", transaction_id="", mchid="1900000001",
            openid="o_payer", delivery_id="SF", tracking_no="SF1",
            description="衣服*1", phone="12345", when=when,
        )
    assert raised.value.message == "顺丰发货需要收件人手机号"
    assert shipping.resolve_delivery_id("顺丰", "") == "SF"
    assert shipping.resolve_delivery_id("随便", "yto") == "YTO"
    with pytest.raises(BizError) as raised:
        shipping.resolve_delivery_id("其他", "")
    assert raised.value.message == "请选择微信支持的快递公司"


async def test_post_treats_already_shipped_as_success_and_hides_body(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"errcode": 10060002, "errmsg": "SECRET_LEAK"})

    monkeypatch.setattr(shipping.wechat, "_access_token", _token("tok-secret"))
    monkeypatch.setattr(httpx, "AsyncClient", _client(handler))
    await shipping._post({"payer": {"openid": "o_payer"}})
    assert "access_token=tok-secret" in seen["url"]
    assert seen["body"]["payer"]["openid"] == "o_payer"

    def leak(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errcode": 10060014, "errmsg": "SECRET_LEAK 13800138000"})

    monkeypatch.setattr(httpx, "AsyncClient", _client(leak))
    with pytest.raises(BizError) as raised:
        await shipping._post({"payer": {"openid": "o_payer"}})
    assert raised.value.message == "发货参数有误"
    assert "SECRET_LEAK" not in raised.value.message
    assert "13800138000" not in raised.value.message
    assert "tok-secret" not in raised.value.message

    monkeypatch.setattr(shipping.wechat, "_access_token", _token(None))
    with pytest.raises(BizError) as raised:
        await shipping._post({})
    assert raised.value.message == "微信发货服务暂不可用，请稍后重试"


async def test_real_ship_rolls_back_when_upload_fails_and_commits_when_it_succeeds(client, monkeypatch):
    admin_h = await admin_login(client)
    user_h = await login(client, "ship-real")
    addr = await client.post("/api/v1/addresses", headers=user_h, json={
        "name": "发货录入", "phone": "13900001111", "region": "", "detail": "路 1 号",
    })
    listing = await client.get("/api/v1/products", params={"q": "穆勒鞋"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    sku = (await client.get(f"/api/v1/products/{spu_id}")).json()["data"]["skus"][0]
    order = (await client.post("/api/v1/orders", headers=user_h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr.json()["data"]["id"],
    })).json()["data"]
    await client.post("/api/v1/payments/mock/confirm", json={"order_no": order["order_no"]})
    async with SessionFactory() as session:
        user = (await session.execute(select(User).where(User.openid == "mock-ship-real"))).scalar_one()
        user.openid = "o_ship_real_openid"
        pay = (await session.execute(select(Payment).where(Payment.order_id == order["id"]))).scalar_one()
        pay.provider = "wechat"
        pay.external_id = "4200000000000099"
        await session.commit()

    calls = {"n": 0}

    async def fail(payload):
        calls["n"] += 1
        calls["payload"] = payload
        raise BizError("微信支付单不存在")

    monkeypatch.setattr(settings, "mock_mode", False)
    monkeypatch.setattr(shipping, "_post", fail)
    resp = await client.post(
        f"/api/admin/orders/{order['id']}/ship", headers=admin_h,
        json={"company": "顺丰速运", "tracking_no": "SF998877", "express_code": "SF"},
    )
    assert resp.status_code == 400
    assert resp.json()["message"] == "微信支付单不存在"
    assert calls["payload"]["order_key"]["transaction_id"] == "4200000000000099"
    assert calls["payload"]["shipping_list"][0]["contact"]["receiver_contact"] == "139****1111"
    assert "13900001111" not in json.dumps(calls["payload"])
    async with SessionFactory() as session:
        saved = (await session.execute(select(Order).where(Order.id == order["id"]))).scalar_one()
        assert saved.status == "pending_shipment"
        assert saved.shipment is None

    async def ok(payload):
        calls["n"] += 1
        return None

    monkeypatch.setattr(shipping, "_post", ok)
    resp = await client.post(
        f"/api/admin/orders/{order['id']}/ship", headers=admin_h,
        json={"company": "顺丰速运", "tracking_no": "SF998877", "express_code": "SF"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "pending_receipt"
    detail = (await client.get(f"/api/v1/orders/{order['id']}", headers=user_h)).json()["data"]
    assert detail["shipment"]["company"] == "顺丰速运"
    assert detail["shipment"]["tracking_no"] == "SF998877"
    assert calls["n"] == 2


_AsyncClient = httpx.AsyncClient


def _token(value):
    async def inner():
        return value
    return inner


def _client(handler):
    def factory(*args, **kwargs):
        return _AsyncClient(transport=httpx.MockTransport(handler))
    return factory
