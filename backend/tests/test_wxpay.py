"""微信支付 JSAPI 与回调。用本地密钥对，不访问微信，也不改 MOCK_MODE。"""

import base64
import json
import re
import time
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select

from app.config import settings
from app.db import SessionFactory
from app.errors import BizError
from app.models.order import Order, Payment, Refund
from app.services.payment import WechatPayProvider
from app.services.wxpay import WxPayClient
from app.utils import utcnow
from tests.conftest import login

APPID = "wx_test_appid"
MCHID = "1900000001"
SERIAL = "SERIALTEST"
PUBID = "PUB_KEY_ID_TEST"
API_KEY = "a" * 32
NOTIFY_URL = "https://example.com/jetset/api/v1/payments/wechat/notify"
_SETTING_FIELDS = (
    "wechat_appid", "wxpay_mchid", "wxpay_cert_serial", "wxpay_private_key_path",
    "wxpay_apiv3_key", "wxpay_notify_url", "wxpay_public_key_path", "wxpay_public_key_id",
)


@pytest.fixture(scope="module")
def private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _pem_private(key) -> bytes:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )


def _pem_public(key) -> bytes:
    return key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _rsa_sign(key, message: bytes) -> str:
    signature = key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("ascii")


def _client(private_key, http, **kw) -> WxPayClient:
    values = dict(
        appid=APPID, mchid=MCHID, cert_serial=SERIAL, private_key=private_key,
        apiv3_key=API_KEY, notify_url=NOTIFY_URL, public_key=private_key.public_key(),
        public_key_id=PUBID, http=http,
    )
    values.update(kw)
    return WxPayClient(**values)


def _signed_prepay(private_key, prepay_id="wx_prepay_test_1"):
    body = json.dumps({"prepay_id": prepay_id}, separators=(",", ":")).encode()
    ts = str(int(time.time()))
    nonce = "resp-nonce"
    message = f"{ts}\n{nonce}\n".encode() + body + b"\n"
    return body, {
        "Content-Type": "application/json",
        "Wechatpay-Timestamp": ts,
        "Wechatpay-Nonce": nonce,
        "Wechatpay-Signature": _rsa_sign(private_key, message),
        "Wechatpay-Serial": PUBID,
    }


@pytest.fixture
def wx_settings(tmp_path, private_key):
    key_path = tmp_path / "apiclient_key.pem"
    pub_path = tmp_path / "wxp_pub.pem"
    key_path.write_bytes(_pem_private(private_key))
    pub_path.write_bytes(_pem_public(private_key))
    saved = {name: getattr(settings, name) for name in _SETTING_FIELDS}
    settings.wechat_appid = APPID
    settings.wxpay_mchid = MCHID
    settings.wxpay_cert_serial = SERIAL
    settings.wxpay_private_key_path = str(key_path)
    settings.wxpay_apiv3_key = API_KEY
    settings.wxpay_notify_url = NOTIFY_URL
    settings.wxpay_public_key_path = str(pub_path)
    settings.wxpay_public_key_id = PUBID
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(settings, name, value)


def _notify_bytes(txn: dict, nonce: str) -> bytes:
    plain = json.dumps(txn, ensure_ascii=False, separators=(",", ":")).encode()
    ciphertext = AESGCM(API_KEY.encode()).encrypt(nonce.encode(), plain, b"transaction")
    payload = {
        "id": "EV-test",
        "create_time": "2026-11-24T12:00:00+08:00",
        "resource_type": "encrypt-resource",
        "event_type": "TRANSACTION.SUCCESS",
        "summary": "支付成功",
        "resource": {
            "original_type": "transaction",
            "algorithm": "AEAD_AES_256_GCM",
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "associated_data": "transaction",
            "nonce": nonce,
        },
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()


def _notify_headers(private_key, body: bytes, ts: str | None = None, serial: str = PUBID) -> dict:
    ts = ts or str(int(time.time()))
    nonce = "notify-nonce"
    message = f"{ts}\n{nonce}\n".encode() + body + b"\n"
    return {
        "Content-Type": "application/json",
        "Wechatpay-Timestamp": ts,
        "Wechatpay-Nonce": nonce,
        "Wechatpay-Signature": _rsa_sign(private_key, message),
        "Wechatpay-Serial": serial,
    }


def _txn(order_no: str, openid: str, total: int, **overrides) -> dict:
    data = {
        "mchid": MCHID,
        "appid": APPID,
        "out_trade_no": order_no,
        "transaction_id": "4200000000000000000000000001",
        "trade_state": "SUCCESS",
        "payer": {"openid": openid},
        "amount": {"total": total, "payer_total": total - 1, "currency": "CNY"},
    }
    data.update(overrides)
    return data


async def _create_order(client, code: str) -> tuple[dict, dict]:
    headers = await login(client, code)
    addr = await client.post("/api/v1/addresses", headers=headers, json={
        "name": "张三", "phone": "13800138000",
        "region": "浙江省 杭州市 西湖区", "detail": "文一西路 100 号",
    })
    listing = await client.get("/api/v1/products", params={"q": "连衣裙"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    detail = await client.get(f"/api/v1/products/{spu_id}")
    sku = detail.json()["data"]["skus"][0]
    resp = await client.post("/api/v1/orders", headers=headers, json={
        "items": [{"sku_id": sku["id"], "qty": 1}], "address_id": addr.json()["data"]["id"],
    })
    assert resp.status_code == 200, resp.text
    return headers, resp.json()["data"]


async def _post_notify(client, private_key, txn: dict, nonce: str, **header_kw):
    body = _notify_bytes(txn, nonce)
    headers = _notify_headers(private_key, body, **header_kw)
    return await client.post("/api/v1/payments/wechat/notify", content=body, headers=headers)


async def _saved(order_no: str) -> tuple[str, list[tuple]]:
    async with SessionFactory() as session:
        order = (await session.execute(select(Order).where(Order.order_no == order_no))).scalar_one()
        pays = (await session.execute(select(Payment).where(Payment.order_id == order.id))).scalars().all()
        return order.status, [(p.provider, p.external_id, p.amount, p.status) for p in pays]


async def test_jsapi_request_is_signed_and_paysign_verifies(private_key):
    seen = {}
    expire = utcnow() + timedelta(minutes=20)

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["body"] = request.content
        seen["auth"] = request.headers["Authorization"]
        seen["accept_encoding"] = request.headers.get("Accept-Encoding")
        body, headers = _signed_prepay(private_key)
        return httpx.Response(200, content=body, headers=headers)

    order = SimpleNamespace(
        order_no="202611241200000001", pay_amount=239900, expire_at=expire,
        items=[SimpleNamespace(name="羽" * 80), SimpleNamespace(name="裤子")],
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        params = await WechatPayProvider(_client(private_key, http)).create_payment(order, "o_real_openid")

    assert seen["method"] == "POST"
    assert seen["accept_encoding"] == "identity"
    assert seen["path"] == "/v3/pay/transactions/jsapi"
    payload = json.loads(seen["body"])
    assert payload["appid"] == APPID
    assert payload["mchid"] == MCHID
    assert payload["out_trade_no"] == order.order_no
    assert payload["notify_url"] == NOTIFY_URL
    assert payload["amount"] == {"total": 239900, "currency": "CNY"}
    assert payload["payer"] == {"openid": "o_real_openid"}
    assert payload["time_expire"] == expire.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    assert payload["description"].endswith("等")
    assert set(payload["description"]) <= {"羽", "等"}
    assert len(payload["description"].encode()) <= 127

    auth = seen["auth"]
    assert auth.startswith("WECHATPAY2-SHA256-RSA2048 ")
    token = auth.split(" ", 1)[1]
    assert ", " not in token
    fields = dict(re.findall(r'([a-z_]+)="([^"]*)"', token))
    assert fields["mchid"] == MCHID
    assert fields["serial_no"] == SERIAL
    message = (
        f"POST\n/v3/pay/transactions/jsapi\n{fields['timestamp']}\n{fields['nonce_str']}\n".encode()
        + seen["body"] + b"\n"
    )
    private_key.public_key().verify(
        base64.b64decode(fields["signature"]), message, padding.PKCS1v15(), hashes.SHA256(),
    )

    assert params["provider"] == "wechat"
    assert params["signType"] == "RSA"
    assert params["package"] == "prepay_id=wx_prepay_test_1"
    assert isinstance(params["timeStamp"], str)
    pay_message = f"{APPID}\n{params['timeStamp']}\n{params['nonceStr']}\n{params['package']}\n".encode()
    private_key.public_key().verify(
        base64.b64decode(params["paySign"]), pay_message, padding.PKCS1v15(), hashes.SHA256(),
    )


async def test_wechat_error_body_is_not_shown(private_key):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, content=b'{"code":"OUT_TRADE_NO_USED","message":"SECRET_LEAK"}')

    order = SimpleNamespace(order_no="202611241200000002", pay_amount=100, expire_at=None, items=[])
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(BizError) as raised:
            await _client(private_key, http).jsapi_params(order, "o_real_openid")
    assert raised.value.message == "请勿重复发起支付"
    assert "SECRET_LEAK" not in raised.value.message

    def unsigned(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b'{"prepay_id":"wx_fake_prepay_01"}')

    async with httpx.AsyncClient(transport=httpx.MockTransport(unsigned)) as http:
        with pytest.raises(BizError) as raised:
            await _client(private_key, http).jsapi_params(order, "o_real_openid")
    assert raised.value.message == "微信支付应答验签失败"
    assert "wx_fake" not in raised.value.message


async def test_mock_openid_and_zero_amount_do_not_call_wechat(private_key):
    def explode(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not call wechat")

    order = SimpleNamespace(order_no="202611241200000003", pay_amount=100, expire_at=None, items=[])
    async with httpx.AsyncClient(transport=httpx.MockTransport(explode)) as http:
        wx = _client(private_key, http)
        with pytest.raises(BizError) as raised:
            await wx.jsapi_params(order, "mock-user")
        assert "不能发起微信支付" in raised.value.message
        order.pay_amount = 0
        with pytest.raises(BizError) as raised:
            await wx.jsapi_params(order, "o_real_openid")
        assert raised.value.message == "支付金额无效"


async def test_pay_route_passes_openid(client, monkeypatch):
    captured = {}

    class Capture:
        async def create_payment(self, order, openid=""):
            captured["openid"] = openid
            return {"provider": "mock", "order_no": order.order_no}

    monkeypatch.setattr("app.api.orders.get_provider", lambda: Capture())
    headers, order = await _create_order(client, "wxpay-pass")
    resp = await client.post(f"/api/v1/orders/{order['id']}/pay", headers=headers)
    assert resp.status_code == 200, resp.text
    assert captured["openid"] == "mock-wxpay-pass"
    assert resp.json()["data"]["provider"] == "mock"


async def test_notify_marks_paid_and_replay_is_idempotent(client, wx_settings, private_key):
    _, order = await _create_order(client, "wxpay-ok")
    openid = "mock-wxpay-ok"
    txn = _txn(order["order_no"], openid, order["pay_amount"])

    bad_amount = _txn(order["order_no"], openid, order["pay_amount"] + 1)
    resp = await _post_notify(client, private_key, bad_amount, "nonce-amount1")
    assert resp.status_code == 400
    assert resp.json() == {"code": "FAIL", "message": "金额不匹配"}
    assert (await _saved(order["order_no"]))[0] == "pending_payment"

    bad_currency = _txn(order["order_no"], openid, order["pay_amount"],
                        amount={"total": order["pay_amount"], "currency": "USD"})
    resp = await _post_notify(client, private_key, bad_currency, "nonce-currency")
    assert resp.status_code == 400
    assert (await _saved(order["order_no"]))[0] == "pending_payment"

    ignored = _txn(order["order_no"], openid, order["pay_amount"], trade_state="NOTPAY")
    resp = await _post_notify(client, private_key, ignored, "nonce-notpay")
    assert resp.status_code == 200
    assert resp.json() == {"code": "SUCCESS", "message": "成功"}
    assert (await _saved(order["order_no"]))[0] == "pending_payment"

    resp = await _post_notify(client, private_key, txn, "nonce-success1")
    assert resp.status_code == 200
    assert resp.json() == {"code": "SUCCESS", "message": "成功"}
    status, pays = await _saved(order["order_no"])
    assert status == "pending_shipment"
    assert pays == [("wechat", txn["transaction_id"], order["pay_amount"], "paid")]

    resp = await _post_notify(client, private_key, txn, "nonce-success1")
    assert resp.status_code == 200
    assert resp.json()["code"] == "SUCCESS"
    status, pays = await _saved(order["order_no"])
    assert status == "pending_shipment"
    assert len(pays) == 1


async def test_notify_bad_signature_does_not_pay(client, wx_settings, private_key):
    _, order = await _create_order(client, "wxpay-bad-sign")
    body = _notify_bytes(_txn(order["order_no"], "mock-wxpay-bad-sign", order["pay_amount"]), "nonce-badsig")
    headers = _notify_headers(private_key, body)
    headers["Wechatpay-Signature"] = base64.b64encode(b"\x01" * 256).decode()
    resp = await client.post("/api/v1/payments/wechat/notify", content=body, headers=headers)
    assert resp.status_code == 401
    assert resp.json() == {"code": "FAIL", "message": "验签失败"}
    assert "data" not in resp.json()
    assert (await _saved(order["order_no"]))[0] == "pending_payment"

    resp = await _post_notify(
        client, private_key, _txn(order["order_no"], "mock-wxpay-bad-sign", order["pay_amount"]),
        "nonce-old", ts=str(int(time.time()) - 1000),
    )
    assert resp.status_code == 401
    assert (await _saved(order["order_no"]))[0] == "pending_payment"

    resp = await _post_notify(
        client, private_key, _txn(order["order_no"], "mock-wxpay-bad-sign", order["pay_amount"]),
        "nonce-serial", serial="PUB_KEY_ID_OTHER",
    )
    assert resp.status_code == 401


async def test_notify_rejects_mismatch_and_closed_order(client, wx_settings, private_key):
    resp = await _post_notify(client, private_key, _txn("202611249999000099", "mock-none", 100), "nonce-missing")
    assert resp.status_code == 404
    assert resp.json()["code"] == "FAIL"

    _, order = await _create_order(client, "wxpay-mismatch")
    resp = await _post_notify(
        client, private_key, _txn(order["order_no"], "mock-wxpay-mismatch", order["pay_amount"], mchid="1999999999"),
        "nonce-mch",
    )
    assert resp.status_code == 400
    assert resp.json()["message"] == "商户信息不匹配"

    resp = await _post_notify(
        client, private_key, _txn(order["order_no"], "o_someone_else", order["pay_amount"]),
        "nonce-payer",
    )
    assert resp.status_code == 400
    assert resp.json()["message"] == "付款人不匹配"
    assert (await _saved(order["order_no"]))[0] == "pending_payment"

    headers, order = await _create_order(client, "wxpay-closed")
    cancelled = await client.post(f"/api/v1/orders/{order['id']}/cancel", headers=headers)
    assert cancelled.json()["data"]["status"] == "cancelled"
    resp = await _post_notify(
        client, private_key, _txn(order["order_no"], "mock-wxpay-closed", order["pay_amount"]),
        "nonce-closed",
    )
    assert resp.status_code == 500
    assert resp.json() == {"code": "FAIL", "message": "订单已关闭"}
    status, pays = await _saved(order["order_no"])
    assert status == "cancelled"
    assert pays == []


def _signed_json(private_key, payload: dict) -> tuple[bytes, dict]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    ts = str(int(time.time()))
    nonce = "refund-nonce"
    message = f"{ts}\n{nonce}\n".encode() + body + b"\n"
    return body, {
        "Content-Type": "application/json",
        "Wechatpay-Timestamp": ts,
        "Wechatpay-Nonce": nonce,
        "Wechatpay-Signature": _rsa_sign(private_key, message),
        "Wechatpay-Serial": PUBID,
    }


async def _stock(client, order: dict) -> int:
    item = order["items"][0]
    detail = (await client.get(f"/api/v1/products/{item['spu_id']}")).json()["data"]
    return next(row["stock"] for row in detail["skus"] if row["id"] == item["sku_id"])


async def test_create_refund_is_signed_and_hides_wechat_body(private_key):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.content
        seen["auth"] = request.headers["Authorization"]
        seen["accept_encoding"] = request.headers.get("Accept-Encoding")
        payload = json.loads(request.content)
        body, headers = _signed_json(private_key, {
            "refund_id": "5030000000000000000000000001",
            "out_refund_no": payload["out_refund_no"],
            "out_trade_no": payload["out_trade_no"],
            "status": "PROCESSING",
            "amount": payload["amount"],
            "user_received_account": "SECRET_LEAK",
        })
        return httpx.Response(200, content=body, headers=headers)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        result = await _client(private_key, http).create_refund(
            out_trade_no="202611241200000009",
            out_refund_no="R202611241200000009",
            amount=239900,
            reason="想" * 90,
        )

    assert seen["path"] == "/v3/refund/domestic/refunds"
    assert seen["accept_encoding"] == "identity"
    payload = json.loads(seen["body"])
    assert payload["notify_url"] == "https://example.com/jetset/api/v1/payments/wechat/refund-notify"
    assert payload["amount"] == {"refund": 239900, "total": 239900, "currency": "CNY"}
    assert payload["reason"] == "想" * 80
    assert payload["out_trade_no"] == "202611241200000009"
    token = seen["auth"].split(" ", 1)[1]
    assert ", " not in token
    fields = dict(re.findall(r'([a-z_]+)="([^"]*)"', token))
    message = (
        f"POST\n/v3/refund/domestic/refunds\n{fields['timestamp']}\n{fields['nonce_str']}\n".encode()
        + seen["body"] + b"\n"
    )
    private_key.public_key().verify(
        base64.b64decode(fields["signature"]), message, padding.PKCS1v15(), hashes.SHA256(),
    )
    assert result == {"status": "PROCESSING", "refund_id": "5030000000000000000000000001"}
    assert "SECRET_LEAK" not in str(result)

    def leak(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, content=b'{"code":"NOT_ENOUGH","message":"SECRET_LEAK"}')

    async with httpx.AsyncClient(transport=httpx.MockTransport(leak)) as http:
        with pytest.raises(BizError) as raised:
            await _client(private_key, http).create_refund(
                out_trade_no="202611241200000009",
                out_refund_no="R202611241200000009",
                amount=100,
                reason="退款",
            )
    assert raised.value.message == "微信账户余额不足，无法退款"
    assert "SECRET_LEAK" not in raised.value.message


async def _seed_processing_refund(order: dict) -> None:
    async with SessionFactory() as session:
        row = (await session.execute(select(Order).where(Order.id == order["id"]))).scalar_one()
        row.status = "refund_pending"
        session.add(Refund(
            order_id=row.id,
            out_refund_no="R" + row.order_no,
            reason="客服确认退款",
            status="processing",
            previous_status="pending_shipment",
            amount=row.pay_amount,
        ))
        await session.commit()


async def test_refund_notify_finalizes_once_and_rejects_bad_money(client, wx_settings, private_key):
    headers, order = await _create_order(client, "wxpay-refund")
    await client.post("/api/v1/payments/mock/confirm", json={"order_no": order["order_no"]})
    stock_paid = await _stock(client, order)
    await _seed_processing_refund(order)
    assert (await _saved(order["order_no"]))[0] == "refund_pending"
    assert await _stock(client, order) == stock_paid

    txn = {
        "mchid": MCHID,
        "out_trade_no": order["order_no"],
        "out_refund_no": "R" + order["order_no"],
        "refund_id": "5030000000000000000000000002",
        "refund_status": "SUCCESS",
        "amount": {"total": order["pay_amount"], "refund": order["pay_amount"], "currency": "CNY"},
        "user_received_account": "SECRET_LEAK",
    }
    bad_amount = dict(txn, amount={"total": order["pay_amount"], "refund": 1, "currency": "CNY"})
    resp = await client.post(
        "/api/v1/payments/wechat/refund-notify",
        content=_notify_bytes(bad_amount, "refund-bad-amt"),
        headers=_notify_headers(private_key, _notify_bytes(bad_amount, "refund-bad-amt")),
    )
    assert resp.status_code == 400
    assert resp.json()["message"] == "金额不匹配"
    assert await _stock(client, order) == stock_paid
    assert (await _saved(order["order_no"]))[0] == "refund_pending"

    body = _notify_bytes(txn, "refund-ok")
    resp = await client.post(
        "/api/v1/payments/wechat/refund-notify",
        content=body, headers=_notify_headers(private_key, body),
    )
    assert resp.status_code == 200
    assert resp.json() == {"code": "SUCCESS", "message": "成功"}
    assert "SECRET_LEAK" not in resp.text
    status, pays = await _saved(order["order_no"])
    assert status == "refunded"
    assert pays[0][3] == "refunded"
    assert await _stock(client, order) == stock_paid + 1

    replay = _notify_bytes(txn, "refund-replay")
    resp = await client.post(
        "/api/v1/payments/wechat/refund-notify",
        content=replay, headers=_notify_headers(private_key, replay),
    )
    assert resp.status_code == 200
    assert await _stock(client, order) == stock_paid + 1

    headers, closed = await _create_order(client, "wxpay-refund-closed")
    await client.post("/api/v1/payments/mock/confirm", json={"order_no": closed["order_no"]})
    await _seed_processing_refund(closed)
    held = await _stock(client, closed)
    closed_txn = dict(txn, out_trade_no=closed["order_no"], out_refund_no="R" + closed["order_no"],
                      refund_status="CLOSED")
    body = _notify_bytes(closed_txn, "refund-closed")
    resp = await client.post(
        "/api/v1/payments/wechat/refund-notify",
        content=body, headers=_notify_headers(private_key, body),
    )
    assert resp.status_code == 200
    assert (await _saved(closed["order_no"]))[0] == "refund_pending"
    detail = (await client.get(f"/api/v1/orders/{closed['id']}", headers=headers)).json()["data"]
    assert detail["refund"]["status"] == "failed"
    assert detail["can_refund"] is False
    assert await _stock(client, closed) == held

    bogus = _notify_bytes(txn, "refund-bogus")
    bad_headers = _notify_headers(private_key, bogus, serial="OTHER")
    resp = await client.post(
        "/api/v1/payments/wechat/refund-notify", content=bogus, headers=bad_headers,
    )
    assert resp.status_code == 401
