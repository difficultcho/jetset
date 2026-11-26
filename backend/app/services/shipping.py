"""微信小程序发货信息录入。

非 mock 时，管理端发货会先调用 upload_shipping_info。失败则不改订单状态。
已发货（10060002）和信息未变化（10060023）视为成功，便于微信已收下、本地未提交时重试。
录入成功后，微信在用户于确认收货组件里确认，或到达自动确认时限后结算。
正式环境确认收货会再查 get_order，只有确认收货或交易完成才把本系统订单收成已完成。
"""

import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.errors import BizError
from app.models.order import Order, Payment
from app.models.user import User
from app.services import wechat
from app.utils import utcnow

logger = logging.getLogger(__name__)

UPLOAD_URL = "https://api.weixin.qq.com/wxa/sec/order/upload_shipping_info"
GET_ORDER_URL = "https://api.weixin.qq.com/wxa/sec/order/get_order"
# 3 确认收货，4 交易完成。2 仍是已发货，不能当成用户已确认。
CONFIRMED_STATES = {3, 4}
# 运力 id 来自发货信息管理使用的 get_delivery_list，不是小店电子面单那套编码。
CARRIERS = (
    ("SF", "顺丰速运"),
    ("YTO", "圆通速递"),
    ("ZTO", "中通快递"),
    ("STO", "申通快递"),
    ("YD", "韵达速递"),
    ("JTSD", "极兔速递"),
    ("JD", "京东物流"),
    ("EMS", "EMS"),
    ("DBL", "德邦快递"),
)
_CODES = {code for code, _name in CARRIERS}
_ALIASES = {name: code for code, name in CARRIERS}
_ALIASES.update({
    "顺丰": "SF",
    "圆通": "YTO",
    "中通": "ZTO",
    "申通": "STO",
    "韵达": "YD",
    "极兔": "JTSD",
    "京东": "JD",
    "德邦": "DBL",
})
_OK = {0, 10060002, 10060023}
_ERRORS = {
    -1: "微信系统繁忙，请稍后重试",
    10060012: "微信系统繁忙，请稍后重试",
    10060019: "微信系统繁忙，请稍后重试",
    10060001: "微信支付单不存在",
    10060003: "该支付单已重新发货过，不能再次录入",
    10060004: "该支付单当前不能发货",
    10060014: "发货参数有误",
    10060031: "支付用户与订单不一致",
    268485216: "发货时间格式有误",
    268485226: "缺少运单号",
    268485227: "缺少快递公司",
}


def resolve_delivery_id(company: str, express_code: str) -> str:
    code = (express_code or "").strip().upper()
    if code:
        if code not in _CODES:
            raise BizError("请选择微信支持的快递公司")
        return code
    alias = _ALIASES.get((company or "").strip())
    if alias:
        return alias
    raise BizError("请选择微信支持的快递公司")


def mask_phone(phone: str) -> str | None:
    """11 位手机号打成 189****1234。顺丰要求末四位可见。"""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if digits.startswith("86") and len(digits) >= 13:
        digits = digits[-11:]
    if len(digits) != 11 or not digits.startswith("1"):
        return None
    return f"{digits[:3]}****{digits[-4:]}"


def item_desc(items) -> str:
    parts = []
    for item in items:
        name = (getattr(item, "name", "") or "").strip() or "商品"
        qty = int(getattr(item, "qty", 1) or 1)
        parts.append(f"{name}*{qty}")
    return ("；".join(parts) if parts else "商品")[:120]


def format_upload_time(when: datetime | None = None) -> str:
    """naive UTC 写成带毫秒的 RFC3339。不把 UTC 标成 +08:00。"""
    when = when or utcnow()
    return when.strftime("%Y-%m-%dT%H:%M:%S") + f".{when.microsecond // 1000:03d}+00:00"


def build_payload(*, order_no: str, transaction_id: str, mchid: str, openid: str,
                  delivery_id: str, tracking_no: str, description: str, phone: str,
                  when: datetime | None = None) -> dict:
    if transaction_id:
        order_key = {"order_number_type": 2, "transaction_id": transaction_id}
    else:
        if not mchid:
            raise BizError("缺少微信支付单号，无法录入发货")
        order_key = {
            "order_number_type": 1,
            "mchid": mchid,
            "out_trade_no": order_no,
        }
    item = {
        "tracking_no": tracking_no,
        "express_company": delivery_id,
        "item_desc": (description or "商品")[:120],
    }
    if delivery_id == "SF":
        masked = mask_phone(phone)
        if not masked:
            raise BizError("顺丰发货需要收件人手机号")
        item["contact"] = {"receiver_contact": masked}
    return {
        "order_key": order_key,
        "logistics_type": 1,
        "delivery_mode": 1,
        "shipping_list": [item],
        "upload_time": format_upload_time(when),
        "payer": {"openid": openid},
    }


async def _post(payload: dict) -> None:
    token = await wechat._access_token()
    if not token:
        logger.warning("发货信息录入失败：access_token 不可用")
        raise BizError("微信发货服务暂不可用，请稍后重试")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(UPLOAD_URL, params={"access_token": token}, json=payload)
            data = resp.json()
    except Exception:
        logger.warning("发货信息录入请求失败")
        raise BizError("微信发货服务暂不可用，请稍后重试") from None
    if not isinstance(data, dict):
        logger.warning("发货信息录入失败：响应无法解析")
        raise BizError("微信发货服务暂不可用，请稍后重试")
    try:
        errcode = int(data.get("errcode", 0))
    except (TypeError, ValueError):
        logger.warning("发货信息录入失败：无 errcode")
        raise BizError("微信发货失败，请稍后重试")
    if errcode in _OK:
        return
    logger.warning("发货信息录入失败 errcode=%s", errcode)
    raise BizError(_ERRORS.get(errcode, "微信发货失败，请稍后重试"))


async def _wechat_json(url: str, payload: dict, log_name: str) -> dict:
    token = await wechat._access_token()
    if not token:
        logger.warning("%s失败：access_token 不可用", log_name)
        raise BizError("微信发货服务暂不可用，请稍后重试")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, params={"access_token": token}, json=payload)
            data = resp.json()
    except Exception:
        logger.warning("%s请求失败", log_name)
        raise BizError("微信发货服务暂不可用，请稍后重试") from None
    if not isinstance(data, dict):
        logger.warning("%s失败：响应无法解析", log_name)
        raise BizError("微信发货服务暂不可用，请稍后重试")
    return data


async def fetch_order_state(transaction_id: str) -> int:
    """查询微信发货状态。失败不把微信报文交出去。"""
    data = await _wechat_json(
        GET_ORDER_URL, {"transaction_id": transaction_id}, "查询发货状态",
    )
    try:
        errcode = int(data.get("errcode", 0) or 0)
    except (TypeError, ValueError):
        errcode = -1
    order = data.get("order") if errcode == 0 else None
    state = order.get("order_state") if isinstance(order, dict) else None
    if not isinstance(state, int):
        logger.warning("查询发货状态失败 errcode=%s", errcode)
        raise BizError("微信发货服务暂不可用，请稍后重试")
    return state


async def submit(session: AsyncSession, order: Order, *, company: str,
                 tracking_no: str, express_code: str = "") -> None:
    """mock 不请求微信。正式环境失败抛 BizError，调用方不要提交订单。"""
    if settings.mock_mode:
        return
    code = resolve_delivery_id(company, express_code)
    user = await session.get(User, order.user_id)
    openid = user.openid if user is not None else ""
    if not openid or openid.startswith("mock-") or any(ch.isspace() for ch in openid):
        raise BizError("当前账号无法录入发货信息")
    pay = (
        await session.execute(
            select(Payment)
            .where(
                Payment.order_id == order.id,
                Payment.provider == "wechat",
                Payment.status == "paid",
            )
            .order_by(Payment.id.desc())
        )
    ).scalars().first()
    transaction_id = pay.external_id if pay is not None and pay.external_id else ""
    snap = order.address_snapshot if isinstance(order.address_snapshot, dict) else {}
    payload = build_payload(
        order_no=order.order_no,
        transaction_id=transaction_id,
        mchid=settings.wxpay_mchid.strip(),
        openid=openid,
        delivery_id=code,
        tracking_no=tracking_no.strip(),
        description=item_desc(order.items),
        phone=str(snap.get("phone") or ""),
    )
    await _post(payload)


async def wechat_transaction_id(session: AsyncSession, order: Order) -> str:
    pay = (
        await session.execute(
            select(Payment)
            .where(Payment.order_id == order.id, Payment.provider == "wechat")
            .order_by(Payment.id.desc())
        )
    ).scalars().first()
    if pay is None or not pay.external_id:
        raise BizError("该订单无法在微信确认收货")
    return pay.external_id


async def wechat_receipts(session: AsyncSession, orders: list[Order]) -> dict[int, dict | None]:
    """给小程序打开确认收货组件用。mock 或没有微信交易号时为空。"""
    found: dict[int, dict | None] = {order.id: None for order in orders}
    mchid = settings.wxpay_mchid.strip()
    if settings.mock_mode or not orders or not mchid:
        return found
    rows = (
        await session.execute(
            select(Payment)
            .where(
                Payment.order_id.in_([order.id for order in orders]),
                Payment.provider == "wechat",
            )
            .order_by(Payment.id.asc())
        )
    ).scalars().all()
    by_order: dict[int, str] = {}
    for pay in rows:
        if pay.external_id:
            by_order[pay.order_id] = pay.external_id
    orders_by_id = {order.id: order for order in orders}
    for order_id, transaction_id in by_order.items():
        order = orders_by_id[order_id]
        found[order_id] = {
            "transaction_id": transaction_id,
            "merchant_id": mchid,
            "merchant_trade_no": order.order_no,
        }
    return found
