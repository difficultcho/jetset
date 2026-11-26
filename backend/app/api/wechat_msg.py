"""小程序消息推送。只处理发货管理的结算事件，并先向微信核对确认收货。"""

import hashlib
import json
import logging
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.deps import DB
from app.errors import BizError
from app.models.order import Order, OrderStatus
from app.services import shipping
from app.services.orders import _finish_order
from app.utils import utcnow

logger = logging.getLogger(__name__)

router = APIRouter()
_MAX_BODY = 65536


def _signature(token: str, timestamp: str, nonce: str) -> str:
    parts = sorted((token, timestamp, nonce))
    return hashlib.sha1("".join(parts).encode()).hexdigest()


def _signed(request: Request) -> bool:
    token = settings.wechat_msg_token.strip()
    if not token:
        return False
    timestamp = request.query_params.get("timestamp") or ""
    nonce = request.query_params.get("nonce") or ""
    signature = request.query_params.get("signature") or ""
    if not timestamp or not nonce or not signature:
        return False
    return _signature(token, timestamp, nonce) == signature


def _xml_event(text: str) -> dict:
    upper = text.upper()
    if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
        return {}
    root = ET.fromstring(text)
    return {child.tag: (child.text or "").strip() for child in list(root)}


def _event(raw: bytes) -> dict:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text or text.startswith("{"):
        try:
            data = json.loads(text or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
    if text.startswith("<"):
        try:
            return _xml_event(text)
        except ET.ParseError:
            return {}
    return {}


def _present(value) -> bool:
    return value not in (None, "", 0, "0")


@router.get("/wechat/message")
async def verify_message(request: Request):
    """微信保存消息推送 URL 时的校验。原样返回 echostr。"""
    if not _signed(request):
        return PlainTextResponse("forbidden", status_code=401)
    return PlainTextResponse(request.query_params.get("echostr") or "")


@router.post("/wechat/message")
async def receive_message(request: Request, session: DB):
    """结算消息。发货时的那一次推送没有确认时间，不改订单。"""
    if not settings.wechat_msg_token.strip():
        return PlainTextResponse("unconfigured", status_code=503)
    if not _signed(request):
        return PlainTextResponse("forbidden", status_code=401)
    raw = await request.body()
    if len(raw) > _MAX_BODY:
        return PlainTextResponse("success")
    event = _event(raw)
    if event.get("Encrypt"):
        logger.warning("发货结算消息是加密的，未处理")
        return PlainTextResponse("success")
    if event.get("Event") != "trade_manage_order_settlement":
        return PlainTextResponse("success")
    if not _present(event.get("confirm_receive_time")) and not _present(event.get("settlement_time")):
        return PlainTextResponse("success")
    merchant_id = str(event.get("merchant_id") or "")
    if merchant_id and merchant_id != settings.wxpay_mchid.strip():
        return PlainTextResponse("success")
    trade_no = event.get("merchant_trade_no")
    if not isinstance(trade_no, str) or not trade_no:
        return PlainTextResponse("success")
    order = (
        await session.execute(
            select(Order).options(selectinload(Order.items)).where(Order.order_no == trade_no)
        )
    ).scalar_one_or_none()
    if order is None or order.status != OrderStatus.PENDING_RECEIPT:
        return PlainTextResponse("success")
    event_txn = event.get("transaction_id")
    try:
        txn = await shipping.wechat_transaction_id(session, order)
    except BizError:
        return PlainTextResponse("success")
    if isinstance(event_txn, str) and event_txn and event_txn != txn:
        return PlainTextResponse("success")
    try:
        state = await shipping.fetch_order_state(txn)
    except BizError:
        logger.warning("结算消息核对微信失败 order=%s", trade_no)
        return PlainTextResponse("retry", status_code=503)
    if state not in shipping.CONFIRMED_STATES:
        return PlainTextResponse("success")
    _finish_order(order, utcnow())
    await session.commit()
    return PlainTextResponse("success")
