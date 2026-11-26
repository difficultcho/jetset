"""微信支付 API v3：JSAPI 下单、小程序调起参数、回调验签与解密。

用已经依赖的 cryptography 做 RSA-SHA256 和 AES-256-GCM，不引入 wechatpayv3。
商户私钥只从 WXPAY_PRIVATE_KEY_PATH 读取，回调用微信支付公钥验签（公钥 ID 对上
Wechatpay-Serial）。两份 PEM 都不进仓库。
"""

import base64
import json
import logging
import re
import secrets
import time
from datetime import timedelta
from pathlib import Path

import httpx
from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings
from app.errors import BizError
from app.utils import utcnow

logger = logging.getLogger(__name__)

JSAPI_PATH = "/v3/pay/transactions/jsapi"
JSAPI_URL = "https://api.mch.weixin.qq.com" + JSAPI_PATH
REFUND_PATH = "/v3/refund/domestic/refunds"
REFUND_URL = "https://api.mch.weixin.qq.com" + REFUND_PATH
AUTH_SCHEME = "WECHATPAY2-SHA256-RSA2048"
SKEW_SECONDS = 300
_ORDER_NO = re.compile(r"[0-9A-Za-z_\-|*]{6,32}")
_REFUND_NO = re.compile(r"[0-9A-Za-z_\-|*]{6,64}")
_PREPAY_ID = re.compile(r"[A-Za-z0-9_\-]{10,64}")
_WECHAT_CODE = re.compile(r"[A-Z0-9_]{1,32}")
_REFUND_STATUS = {"SUCCESS", "PROCESSING", "CLOSED", "ABNORMAL"}

# 只映射已知错误码。微信原文可能带请求细节，不回给前端。
_WECHAT_ERRORS = {
    "ORDERPAID": "订单已支付",
    "ORDERCLOSED": "订单已关闭，请重新下单",
    "OUT_TRADE_NO_USED": "请勿重复发起支付",
    "APPID_MCHID_NOT_MATCH": "微信支付商户与小程序未绑定",
    "NO_AUTH": "微信支付权限未开通",
    "MCH_NOT_EXISTS": "微信支付商户号无效",
    "SIGN_ERROR": "微信支付签名失败",
}
_REFUND_ERRORS = {
    "NOT_ENOUGH": "微信账户余额不足，无法退款",
    "RESOURCE_NOT_EXISTS": "微信侧找不到该支付单",
    "ORDER_NOT_EXIST": "微信侧找不到该支付单",
    "FREQUENCY_LIMITED": "退款请求过于频繁，请稍后重试",
    "USER_ACCOUNT_ABNORMAL": "用户账户异常，无法原路退款",
    "INVALID_REQUEST": "退款请求无效",
    "PARAM_ERROR": "退款请求无效",
    "SYSTEM_ERROR": "微信退款暂不可用，请稍后重试",
    "SIGN_ERROR": "微信支付签名失败",
    "NO_AUTH": "微信支付退款权限未开通",
    "MCH_NOT_EXISTS": "微信支付商户号无效",
}


class NotifyError(Exception):
    """回调处理失败。路由把它直接写成微信要求的 {code: FAIL}，不走业务信封。"""

    def __init__(self, http_status: int, message: str):
        self.http_status = http_status
        self.message = message
        super().__init__(message)


def _sign(private_key, message: bytes) -> str:
    signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("ascii")


def _request_message(method: str, path: str, timestamp: str, nonce: str, body: bytes) -> bytes:
    head = f"{method}\n{path}\n{timestamp}\n{nonce}\n".encode()
    return head + body + b"\n"


def callback_message(timestamp: str, nonce: str, body: bytes) -> bytes:
    """应答和回调用同一段：timestamp、nonce、报文，各以换行结束。"""
    return f"{timestamp}\n{nonce}\n".encode() + body + b"\n"


def _authorization(mchid: str, serial: str, private_key, method: str, path: str, body: bytes) -> tuple[str, str, str]:
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    signature = _sign(private_key, _request_message(method, path, timestamp, nonce, body))
    # 逗号后不加空格，与微信官方 SDK 的 Authorization 一致。
    token = (
        f'mchid="{mchid}",nonce_str="{nonce}",timestamp="{timestamp}",'
        f'serial_no="{serial}",signature="{signature}"'
    )
    return f"{AUTH_SCHEME} {token}", timestamp, nonce


def _clip_utf8(text: str, limit: int) -> str:
    raw = text.encode("utf-8")
    if len(raw) <= limit:
        return text
    return raw[:limit].decode("utf-8", errors="ignore")


def refund_notify_url(notify_url: str) -> str:
    """支付回调是 …/notify，退款回调换成同目录的 …/refund-notify。不新增环境变量。"""
    base = (notify_url or "").strip().rstrip("/")
    if not base.startswith("https://") or not base.endswith("/notify"):
        raise BizError("微信支付未配置完整", http_status=503)
    return base[:-len("notify")] + "refund-notify"


def description_for(order) -> str:
    """商品描述，UTF-8 不超过 127 字节。多件时在第一件名称后加「等」。"""
    items = list(getattr(order, "items", None) or [])
    first = ""
    for item in items:
        name = (getattr(item, "name", "") or "").strip()
        if name:
            first = name
            break
    if not first:
        first = "JET SET"
    suffix = "等" if len(items) > 1 else ""
    room = 127 - len(suffix.encode("utf-8"))
    if room < 1:
        return _clip_utf8(suffix, 127)
    return _clip_utf8(first, room) + suffix


def _time_expire(order) -> str | None:
    expire = getattr(order, "expire_at", None)
    if expire is None:
        return None
    if expire <= utcnow() + timedelta(seconds=60):
        return None
    return expire.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _read_pem(path: str, kind: str):
    try:
        data = Path(path).read_bytes()
    except OSError:
        raise BizError("微信支付未配置完整", http_status=503) from None
    try:
        if kind == "private":
            return serialization.load_pem_private_key(data, password=None)
        return serialization.load_pem_public_key(data)
    except (ValueError, TypeError):
        raise BizError("微信支付未配置完整", http_status=503) from None


def verify_signature(public_key, *, public_key_id: str, timestamp: str, nonce: str,
                     body: bytes, signature: str, serial: str) -> None:
    timestamp = (timestamp or "").strip()
    nonce = (nonce or "").strip()
    signature = (signature or "").strip()
    serial = (serial or "").strip()
    if not timestamp or not nonce or not signature or not serial:
        raise NotifyError(401, "验签失败")
    if serial != public_key_id.strip():
        raise NotifyError(401, "验签失败")
    try:
        ts = int(timestamp)
    except ValueError:
        raise NotifyError(401, "验签失败") from None
    if abs(int(time.time()) - ts) > SKEW_SECONDS:
        raise NotifyError(401, "验签失败")
    try:
        raw_sig = base64.b64decode(signature, validate=True)
    except (ValueError, TypeError):
        raise NotifyError(401, "验签失败") from None
    try:
        public_key.verify(
            raw_sig, callback_message(timestamp, nonce, body),
            padding.PKCS1v15(), hashes.SHA256(),
        )
    except InvalidSignature:
        raise NotifyError(401, "验签失败") from None


def decrypt_resource(apiv3_key: str, resource: dict) -> dict:
    key = apiv3_key.strip().encode("utf-8")
    if len(key) != 32:
        raise NotifyError(503, "微信支付未配置")
    if not isinstance(resource, dict) or resource.get("algorithm") != "AEAD_AES_256_GCM":
        raise NotifyError(400, "回调数据无效")
    nonce = resource.get("nonce")
    ciphertext = resource.get("ciphertext")
    if not isinstance(nonce, str) or not nonce or not isinstance(ciphertext, str):
        raise NotifyError(400, "回调数据无效")
    aad = resource.get("associated_data")
    if not isinstance(aad, str):
        aad = ""
    try:
        plain = AESGCM(key).decrypt(nonce.encode("utf-8"), base64.b64decode(ciphertext), aad.encode("utf-8"))
        data = json.loads(plain)
    except (InvalidTag, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        raise NotifyError(400, "回调数据无效") from None
    if not isinstance(data, dict):
        raise NotifyError(400, "回调数据无效")
    return data


def parse_notify(raw: bytes, headers, *, public_key, public_key_id: str, apiv3_key: str) -> dict:
    """验签后解密，返回交易对象。失败抛 NotifyError，不带报文内容。"""
    verify_signature(
        public_key,
        public_key_id=public_key_id,
        timestamp=(headers.get("Wechatpay-Timestamp") or "").strip(),
        nonce=(headers.get("Wechatpay-Nonce") or "").strip(),
        body=raw,
        signature=(headers.get("Wechatpay-Signature") or "").strip(),
        serial=(headers.get("Wechatpay-Serial") or "").strip(),
    )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise NotifyError(400, "回调数据无效") from None
    if not isinstance(payload, dict):
        raise NotifyError(400, "回调数据无效")
    return decrypt_resource(apiv3_key, payload.get("resource"))


class WxPayClient:
    def __init__(self, *, appid: str, mchid: str, cert_serial: str, private_key,
                 apiv3_key: str, notify_url: str, public_key, public_key_id: str,
                 http: httpx.AsyncClient | None = None):
        self.appid = appid.strip()
        self.mchid = mchid.strip()
        self.cert_serial = cert_serial.strip()
        self.private_key = private_key
        self.apiv3_key = apiv3_key.strip()
        self.notify_url = notify_url.strip()
        self.public_key = public_key
        self.public_key_id = public_key_id.strip()
        self._http = http
        if len(self.apiv3_key.encode("utf-8")) != 32 or not self.notify_url.startswith("https://"):
            raise BizError("微信支付未配置完整", http_status=503)

    async def jsapi_params(self, order, openid: str) -> dict:
        if not openid or openid.startswith("mock-") or any(ch.isspace() for ch in openid):
            raise BizError("当前账号不能发起微信支付")
        if not isinstance(order.pay_amount, int) or order.pay_amount < 1:
            raise BizError("支付金额无效")
        if not _ORDER_NO.fullmatch(order.order_no or ""):
            raise BizError("订单号无法用于微信支付")

        payload = {
            "appid": self.appid,
            "mchid": self.mchid,
            "description": description_for(order),
            "out_trade_no": order.order_no,
            "notify_url": self.notify_url,
            "amount": {"total": order.pay_amount, "currency": "CNY"},
            "payer": {"openid": openid},
        }
        expire = _time_expire(order)
        if expire:
            payload["time_expire"] = expire
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        authorization, _, _ = _authorization(
            self.mchid, self.cert_serial, self.private_key, "POST", JSAPI_PATH, body,
        )
        headers = {
            "Authorization": authorization,
            "Accept": "application/json",
            # 关掉压缩。应答验签用的是报文原文，压缩后再验会对不上。
            "Accept-Encoding": "identity",
            "Content-Type": "application/json",
            "User-Agent": "jetset-shop/wxpay",
        }
        try:
            if self._http is not None:
                resp = await self._http.post(JSAPI_URL, content=body, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=10) as http:
                    resp = await http.post(JSAPI_URL, content=body, headers=headers)
        except httpx.HTTPError:
            raise BizError("微信支付暂不可用，请稍后重试", http_status=502) from None

        if resp.status_code < 200 or resp.status_code >= 300:
            raise BizError(
                _wechat_error(resp, log_name="jsapi", mapping=_WECHAT_ERRORS,
                              fallback="微信支付下单失败，请稍后重试"),
                http_status=502,
            )
        _verify_response(self.public_key, self.public_key_id, resp)
        try:
            data = json.loads(resp.content)
        except json.JSONDecodeError:
            raise BizError("微信支付下单失败，请稍后重试", http_status=502) from None
        prepay_id = data.get("prepay_id") if isinstance(data, dict) else None
        if not isinstance(prepay_id, str) or not _PREPAY_ID.fullmatch(prepay_id):
            raise BizError("微信支付下单失败，请稍后重试", http_status=502)

        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        package = f"prepay_id={prepay_id}"
        pay_sign = _sign(self.private_key, f"{self.appid}\n{timestamp}\n{nonce}\n{package}\n".encode())
        return {
            "provider": "wechat",
            "timeStamp": timestamp,
            "nonceStr": nonce,
            "package": package,
            "signType": "RSA",
            "paySign": pay_sign,
        }

    async def create_refund(self, *, out_trade_no: str, out_refund_no: str,
                            amount: int, reason: str) -> dict:
        """申请原路退款。只返回状态和微信退款单号，不把微信报文交出去。"""
        if not isinstance(amount, int) or amount < 1:
            raise BizError("退款金额无效")
        if not _ORDER_NO.fullmatch(out_trade_no or ""):
            raise BizError("订单号无法用于微信支付")
        if not _REFUND_NO.fullmatch(out_refund_no or ""):
            raise BizError("退款单号无效")
        payload = {
            "out_trade_no": out_trade_no,
            "out_refund_no": out_refund_no,
            "notify_url": refund_notify_url(self.notify_url),
            "amount": {"refund": amount, "total": amount, "currency": "CNY"},
        }
        text = (reason or "").strip()[:80]
        if text:
            payload["reason"] = text
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        authorization, _, _ = _authorization(
            self.mchid, self.cert_serial, self.private_key, "POST", REFUND_PATH, body,
        )
        headers = {
            "Authorization": authorization,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Content-Type": "application/json",
            "User-Agent": "jetset-shop/wxpay",
        }
        try:
            if self._http is not None:
                resp = await self._http.post(REFUND_URL, content=body, headers=headers)
            else:
                async with httpx.AsyncClient(timeout=10) as http:
                    resp = await http.post(REFUND_URL, content=body, headers=headers)
        except httpx.HTTPError:
            raise BizError("微信退款暂不可用，请稍后重试", http_status=502) from None
        if resp.status_code < 200 or resp.status_code >= 300:
            raise BizError(
                _wechat_error(resp, log_name="refund", mapping=_REFUND_ERRORS,
                              fallback="微信退款失败，请稍后重试"),
                http_status=502,
            )
        _verify_response(self.public_key, self.public_key_id, resp)
        try:
            data = json.loads(resp.content)
        except json.JSONDecodeError:
            raise BizError("微信退款失败，请稍后重试", http_status=502) from None
        if not isinstance(data, dict):
            raise BizError("微信退款失败，请稍后重试", http_status=502)
        status = data.get("status")
        amount_obj = data.get("amount")
        if (status not in _REFUND_STATUS or data.get("out_refund_no") != out_refund_no
                or not isinstance(amount_obj, dict)
                or amount_obj.get("refund") != amount or amount_obj.get("total") != amount
                or amount_obj.get("currency") not in (None, "CNY")):
            raise BizError("微信退款失败，请稍后重试", http_status=502)
        refund_id = data.get("refund_id")
        if not isinstance(refund_id, str) or not refund_id or len(refund_id) > 64:
            refund_id = ""
        return {"status": status, "refund_id": refund_id}


def _wechat_error(resp: httpx.Response, *, log_name: str, mapping: dict[str, str], fallback: str) -> str:
    code = ""
    try:
        data = json.loads(resp.content)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        raw = data.get("code")
        if isinstance(raw, str) and _WECHAT_CODE.fullmatch(raw):
            code = raw
    logger.warning("wxpay %s http %s code %s", log_name, resp.status_code, code or "-")
    return mapping.get(code, fallback)


def _verify_response(public_key, public_key_id: str, resp: httpx.Response) -> None:
    try:
        verify_signature(
            public_key,
            public_key_id=public_key_id,
            timestamp=resp.headers.get("Wechatpay-Timestamp", ""),
            nonce=resp.headers.get("Wechatpay-Nonce", ""),
            body=resp.content,
            signature=resp.headers.get("Wechatpay-Signature", ""),
            serial=resp.headers.get("Wechatpay-Serial", ""),
        )
    except NotifyError:
        raise BizError("微信支付应答验签失败", http_status=502) from None


def client_from_settings() -> WxPayClient:
    required = (
        settings.wechat_appid, settings.wxpay_mchid, settings.wxpay_cert_serial,
        settings.wxpay_private_key_path, settings.wxpay_apiv3_key, settings.wxpay_notify_url,
        settings.wxpay_public_key_path, settings.wxpay_public_key_id,
    )
    if not all(str(item).strip() for item in required):
        raise BizError("微信支付未配置完整", http_status=503)
    return WxPayClient(
        appid=settings.wechat_appid,
        mchid=settings.wxpay_mchid,
        cert_serial=settings.wxpay_cert_serial,
        private_key=_read_pem(settings.wxpay_private_key_path, "private"),
        apiv3_key=settings.wxpay_apiv3_key,
        notify_url=settings.wxpay_notify_url,
        public_key=_read_pem(settings.wxpay_public_key_path, "public"),
        public_key_id=settings.wxpay_public_key_id,
    )
