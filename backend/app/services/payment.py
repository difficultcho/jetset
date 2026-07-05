"""支付渠道抽象。

MVP 用 MockProvider 跑通全流程；微信支付商户号（mchid/证书/APIv3 key）
配置齐全后实现 WechatPayProvider（建议基于 wechatpayv3 库）：
  1. create_payment -> JSAPI 下单，返回小程序 wx.requestPayment 所需参数
  2. /payments/wechat/notify 回调 -> 验签 + 解密 -> mark_order_paid（幂等）
"""

from app.config import settings
from app.errors import BizError
from app.models.order import Order


class MockProvider:
    name = "mock"

    async def create_payment(self, order: Order) -> dict:
        return {
            "provider": "mock",
            "order_no": order.order_no,
            "amount": order.pay_amount,
            "tip": "开发模式：POST /api/v1/payments/mock/confirm {order_no} 即完成支付",
        }


class WechatPayProvider:
    name = "wechat"

    def __init__(self) -> None:
        required = [
            settings.wxpay_mchid,
            settings.wxpay_cert_serial,
            settings.wxpay_private_key_path,
            settings.wxpay_apiv3_key,
            settings.wxpay_notify_url,
        ]
        if not all(required):
            raise BizError("微信支付未配置完整（mchid/证书/APIv3 key）", http_status=503)

    async def create_payment(self, order: Order) -> dict:
        # TODO: 接入 wechatpayv3 JSAPI 下单，需商户号资质
        raise BizError("微信支付渠道尚未实现，请先使用 mock 渠道", http_status=501)


def get_provider():
    if settings.payment_provider == "wechat":
        return WechatPayProvider()
    return MockProvider()
