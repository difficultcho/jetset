"""确认收货与结算消息。不请求微信。"""

import hashlib

import pytest
from sqlalchemy import select

from app.config import settings
from app.db import SessionFactory
from app.errors import BizError
from app.models.order import Order, Payment
from app.services import shipping
from tests.conftest import login
from tests.test_admin import admin_login

TOKEN = "test-msg-token"
MCHID = "1900000001"
TXN = "4200000000001001"


def _sign(timestamp: str, nonce: str, token: str = TOKEN) -> str:
    parts = sorted((token, timestamp, nonce))
    return hashlib.sha1("".join(parts).encode()).hexdigest()


def _query(token: str = TOKEN) -> dict:
    timestamp, nonce = "1700000000", "nonce-confirm"
    return {
        "timestamp": timestamp,
        "nonce": nonce,
        "signature": _sign(timestamp, nonce, token),
    }


async def _forbid(_txn: str) -> int:
    raise AssertionError("不应查询微信")


async def _shipped(client, code: str) -> tuple[dict, dict, dict]:
    admin_h = await admin_login(client)
    user_h = await login(client, code)
    addr = await client.post("/api/v1/addresses", headers=user_h, json={
        "name": "确认收货", "phone": "13900002222", "region": "", "detail": "路 1 号",
    })
    listing = await client.get("/api/v1/products", params={"q": "穆勒鞋"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    sku = (await client.get(f"/api/v1/products/{spu_id}")).json()["data"]["skus"][0]
    order = (await client.post("/api/v1/orders", headers=user_h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr.json()["data"]["id"],
    })).json()["data"]
    await client.post("/api/v1/payments/mock/confirm", json={"order_no": order["order_no"]})
    resp = await client.post(
        f"/api/admin/orders/{order['id']}/ship", headers=admin_h,
        json={"company": "顺丰", "tracking_no": "SF" + code},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "pending_receipt"
    return admin_h, user_h, order


async def _mark_wechat(order_id: int, txn: str = TXN) -> None:
    async with SessionFactory() as session:
        pay = (await session.execute(select(Payment).where(Payment.order_id == order_id))).scalar_one()
        pay.provider = "wechat"
        pay.external_id = txn
        pay.status = "paid"
        await session.commit()


async def _saved(order_id: int) -> Order:
    async with SessionFactory() as session:
        return (await session.execute(select(Order).where(Order.id == order_id))).scalar_one()


def _event(order_no: str, **extra) -> dict:
    body = {
        "Event": "trade_manage_order_settlement",
        "transaction_id": TXN,
        "merchant_id": MCHID,
        "merchant_trade_no": order_no,
        "confirm_receive_method": 1,
        "confirm_receive_time": 1700000100,
        "settlement_time": 1700000101,
    }
    body.update(extra)
    return body


async def test_fetch_order_state_reads_confirmed_int(monkeypatch):
    async def fake(url, payload, log_name):
        assert url == shipping.GET_ORDER_URL
        assert payload == {"transaction_id": "T1"}
        return {"errcode": 0, "order": {"order_state": 4}}

    monkeypatch.setattr(shipping, "_wechat_json", fake)
    assert await shipping.fetch_order_state("T1") == 4


async def test_fetch_order_state_rejects_unparsed_state(monkeypatch):
    async def fake(url, payload, log_name):
        return {"errcode": 0, "order": {"order_state": "3"}}

    monkeypatch.setattr(shipping, "_wechat_json", fake)
    with pytest.raises(BizError) as raised:
        await shipping.fetch_order_state("T1")
    assert raised.value.message == "微信发货服务暂不可用，请稍后重试"


async def test_mock_confirm_stays_local_and_receipt_is_hidden(client):
    _admin_h, user_h, order = await _shipped(client, "confirm-mock")
    detail = (await client.get(f"/api/v1/orders/{order['id']}", headers=user_h)).json()["data"]
    assert detail["wechat_receipt"] is None
    resp = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=user_h)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "completed"
    assert resp.json()["data"]["wechat_receipt"] is None


async def test_receipt_payload_appears_only_for_a_real_wechat_payment(client, monkeypatch):
    _admin_h, user_h, order = await _shipped(client, "confirm-receipt")
    await _mark_wechat(order["id"])
    detail = (await client.get(f"/api/v1/orders/{order['id']}", headers=user_h)).json()["data"]
    assert detail["wechat_receipt"] is None

    monkeypatch.setattr(settings, "mock_mode", False)
    monkeypatch.setattr(settings, "wxpay_mchid", "")
    detail = (await client.get(f"/api/v1/orders/{order['id']}", headers=user_h)).json()["data"]
    assert detail["wechat_receipt"] is None

    monkeypatch.setattr(settings, "wxpay_mchid", MCHID)
    detail = (await client.get(f"/api/v1/orders/{order['id']}", headers=user_h)).json()["data"]
    assert detail["wechat_receipt"] == {
        "transaction_id": TXN,
        "merchant_id": MCHID,
        "merchant_trade_no": order["order_no"],
    }
    listed = (await client.get(
        "/api/v1/orders", headers=user_h, params={"status": "pending_receipt"},
    )).json()["data"]
    row = next(item for item in listed["items"] if item["id"] == order["id"])
    assert row["wechat_receipt"]["merchant_trade_no"] == order["order_no"]


@pytest.mark.parametrize("state", [2, 6])
async def test_real_confirm_rejects_until_wechat_says_received(client, monkeypatch, state):
    _admin_h, user_h, order = await _shipped(client, f"confirm-wait-{state}")
    await _mark_wechat(order["id"], TXN + str(state))

    async def queried(txn):
        assert txn == TXN + str(state)
        return state

    monkeypatch.setattr(settings, "mock_mode", False)
    monkeypatch.setattr(shipping, "fetch_order_state", queried)
    resp = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=user_h)
    assert resp.status_code == 400
    assert resp.json()["message"] == "请先在微信确认收货"
    saved = await _saved(order["id"])
    assert saved.status == "pending_receipt"
    assert saved.completed_at is None


async def test_real_confirm_completes_once_wechat_state_is_received(client, monkeypatch):
    _admin_h, user_h, order = await _shipped(client, "confirm-done")
    await _mark_wechat(order["id"])
    calls = {"n": 0}

    async def queried(_txn):
        calls["n"] += 1
        return 3

    monkeypatch.setattr(settings, "mock_mode", False)
    monkeypatch.setattr(settings, "wxpay_mchid", MCHID)
    monkeypatch.setattr(shipping, "fetch_order_state", queried)
    resp = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=user_h)
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["status"] == "completed"
    assert body["wechat_receipt"]["transaction_id"] == TXN
    done_at = (await _saved(order["id"])).completed_at
    assert done_at is not None

    again = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=user_h)
    assert again.status_code == 200, again.text
    assert again.json()["data"]["status"] == "completed"
    assert (await _saved(order["id"])).completed_at == done_at
    assert calls["n"] == 1


async def test_real_confirm_without_wechat_payment_is_rejected(client, monkeypatch):
    _admin_h, user_h, order = await _shipped(client, "confirm-nopay")
    monkeypatch.setattr(settings, "mock_mode", False)
    monkeypatch.setattr(shipping, "fetch_order_state", _forbid)
    resp = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=user_h)
    assert resp.status_code == 400
    assert resp.json()["message"] == "该订单无法在微信确认收货"
    assert (await _saved(order["id"])).status == "pending_receipt"


async def test_admin_complete_does_not_ask_wechat(client, monkeypatch):
    admin_h, user_h, order = await _shipped(client, "confirm-admin")
    await _mark_wechat(order["id"])
    monkeypatch.setattr(settings, "mock_mode", False)
    monkeypatch.setattr(shipping, "fetch_order_state", _forbid)
    resp = await client.post(f"/api/admin/orders/{order['id']}/complete", headers=admin_h)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "completed"
    again = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=user_h)
    assert again.status_code == 200, again.text
    assert again.json()["data"]["status"] == "completed"


async def _post_event(client, order_no: str, body: dict, params: dict | None = None):
    return await client.post(
        "/api/v1/wechat/message",
        params=params if params is not None else _query(),
        json=body,
    )


async def test_message_requires_token_and_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "wechat_msg_token", "")
    resp = await client.post("/api/v1/wechat/message", json={"Event": "trade_manage_order_settlement"})
    assert resp.status_code == 503
    assert resp.text == "unconfigured"

    monkeypatch.setattr(settings, "wechat_msg_token", TOKEN)
    bad = await client.post(
        "/api/v1/wechat/message",
        params={"timestamp": "1700000000", "nonce": "nonce-confirm", "signature": "0" * 40},
        json={"Event": "trade_manage_order_settlement"},
    )
    assert bad.status_code == 401
    assert bad.text == "forbidden"
    echo = await client.get("/api/v1/wechat/message", params={**_query(), "echostr": "echo-ok"})
    assert echo.status_code == 200
    assert echo.text == "echo-ok"
    blocked = await client.get(
        "/api/v1/wechat/message",
        params={"timestamp": "1", "nonce": "2", "signature": "nope", "echostr": "secret"},
    )
    assert blocked.status_code == 401


async def test_settlement_completes_pending_receipt_once(client, monkeypatch):
    _admin_h, _user_h, order = await _shipped(client, "settle-ok")
    await _mark_wechat(order["id"])
    calls = {"n": 0}

    async def queried(txn):
        calls["n"] += 1
        assert txn == TXN
        return 4

    monkeypatch.setattr(settings, "wechat_msg_token", TOKEN)
    monkeypatch.setattr(settings, "wxpay_mchid", MCHID)
    monkeypatch.setattr(shipping, "fetch_order_state", queried)
    resp = await _post_event(client, order["order_no"], _event(order["order_no"]))
    assert resp.status_code == 200
    assert resp.text == "success"
    saved = await _saved(order["id"])
    assert saved.status == "completed"
    done_at = saved.completed_at
    replay = await _post_event(client, order["order_no"], _event(order["order_no"]))
    assert replay.status_code == 200
    assert replay.text == "success"
    assert (await _saved(order["id"])).completed_at == done_at
    assert calls["n"] == 1


async def test_settlement_ignores_ship_notice_and_unconfirmed_state(client, monkeypatch):
    _admin_h, _user_h, order = await _shipped(client, "settle-early")
    await _mark_wechat(order["id"])
    calls = {"n": 0}

    async def queried(_txn):
        calls["n"] += 1
        return 2

    monkeypatch.setattr(settings, "wechat_msg_token", TOKEN)
    monkeypatch.setattr(settings, "wxpay_mchid", MCHID)
    monkeypatch.setattr(shipping, "fetch_order_state", queried)
    ship_time = _event(
        order["order_no"],
        confirm_receive_time=None,
        settlement_time=None,
        estimated_settlement_time=1700009999,
    )
    resp = await _post_event(client, order["order_no"], ship_time)
    assert resp.status_code == 200
    assert (await _saved(order["id"])).status == "pending_receipt"
    assert calls["n"] == 0

    zeroed = _event(order["order_no"], confirm_receive_time=0, settlement_time="0")
    resp = await _post_event(client, order["order_no"], zeroed)
    assert resp.status_code == 200
    assert calls["n"] == 0

    resp = await _post_event(client, order["order_no"], _event(order["order_no"]))
    assert resp.status_code == 200
    assert (await _saved(order["id"])).status == "pending_receipt"
    assert calls["n"] == 1


async def test_settlement_ignores_mismatch_refund_and_bad_xml(client, monkeypatch):
    admin_h, _user_h, order = await _shipped(client, "settle-skip")
    await _mark_wechat(order["id"])
    monkeypatch.setattr(settings, "wechat_msg_token", TOKEN)
    monkeypatch.setattr(settings, "wxpay_mchid", MCHID)
    monkeypatch.setattr(shipping, "fetch_order_state", _forbid)

    other_mch = await _post_event(
        client, order["order_no"], _event(order["order_no"], merchant_id="999"),
    )
    assert other_mch.status_code == 200
    other_txn = await _post_event(
        client, order["order_no"], _event(order["order_no"], transaction_id="other-txn"),
    )
    assert other_txn.status_code == 200
    encrypted = await _post_event(client, order["order_no"], {
        "Encrypt": "cipher",
        "Event": "trade_manage_order_settlement",
        "merchant_trade_no": order["order_no"],
        "confirm_receive_time": 1700000100,
        "settlement_time": 1700000101,
    })
    assert encrypted.status_code == 200
    assert encrypted.text == "success"
    assert (await _saved(order["id"])).status == "pending_receipt"

    refunded = await client.post(f"/api/admin/orders/{order['id']}/refund", headers=admin_h, json={})
    assert refunded.status_code == 200, refunded.text
    assert refunded.json()["data"]["status"] == "refunded"
    # 退款发生在 mock 模式。上面只改了消息 Token，没有关掉 mock。
    replay = await _post_event(client, order["order_no"], _event(order["order_no"]))
    assert replay.status_code == 200
    assert (await _saved(order["id"])).status == "refunded"

    _admin_h, _user_h, other = await _shipped(client, "settle-xml")
    poisoned = await client.post(
        "/api/v1/wechat/message",
        params=_query(),
        content=b"<?xml version='1.0'?><!DOCTYPE foo [<!ENTITY x 'x'>]><xml><Event>trade_manage_order_settlement</Event></xml>",
    )
    assert poisoned.status_code == 200
    assert poisoned.text == "success"
    assert (await _saved(other["id"])).status == "pending_receipt"


async def test_settlement_retries_when_wechat_check_fails_and_skips_without_payment(client, monkeypatch):
    _admin_h, _user_h, missing = await _shipped(client, "settle-nopay")
    _admin_h, _user_h, order = await _shipped(client, "settle-down")
    await _mark_wechat(order["id"])

    async def down(_txn):
        raise BizError("微信发货服务暂不可用，请稍后重试")

    monkeypatch.setattr(settings, "wechat_msg_token", TOKEN)
    monkeypatch.setattr(settings, "wxpay_mchid", MCHID)
    monkeypatch.setattr(shipping, "fetch_order_state", down)
    skipped = await _post_event(client, missing["order_no"], _event(missing["order_no"]))
    assert skipped.status_code == 200
    assert (await _saved(missing["id"])).status == "pending_receipt"
    retry = await _post_event(client, order["order_no"], _event(order["order_no"]))
    assert retry.status_code == 503
    assert retry.text == "retry"
    assert (await _saved(order["id"])).status == "pending_receipt"
