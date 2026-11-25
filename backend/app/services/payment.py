"""支付渠道。

MOCK_MODE=true 时用 MockProvider，收银台确认后走 /payments/mock/confirm。
关掉后 WechatPayProvider 调微信 JSAPI 下单，支付结果只认验签后的回调。
"""

from app.config import settings
from app.errors import BizError
from app.models.order import Order
from app.services.wxpay import WxPayClient, client_from_settings


class MockProvider:
    name = "mock"

    async def create_payment(self, order: Order, openid: str = "") -> dict:
        return {
            "provider": "mock",
            "order_no": order.order_no,
            "amount": order.pay_amount,
            "tip": "开发模式：POST /api/v1/payments/mock/confirm {order_no} 即完成支付",
        }


class WechatPayProvider:
    name = "wechat"

    def __init__(self, client: WxPayClient | None = None) -> None:
        self._wx = client
        if client is not None:
            return
        required = (
            settings.wechat_appid, settings.wxpay_mchid, settings.wxpay_cert_serial,
            settings.wxpay_private_key_path, settings.wxpay_apiv3_key, settings.wxpay_notify_url,
            settings.wxpay_public_key_path, settings.wxpay_public_key_id,
        )
        if not all(str(item).strip() for item in required):
            raise BizError("微信支付未配置完整", http_status=503)

    async def create_payment(self, order: Order, openid: str = "") -> dict:
        client = self._wx or client_from_settings()
        return await client.jsapi_params(order, openid)


def get_provider():
    """渠道由 MOCK_MODE 单一决定，不再有独立的 PAYMENT_PROVIDER 开关。"""
    return MockProvider() if settings.mock_mode else WechatPayProvider()
