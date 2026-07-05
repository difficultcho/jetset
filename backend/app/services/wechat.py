import httpx

from app.config import settings
from app.errors import BizError

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


async def code2session(code: str) -> dict:
    """wx.login 的 code 换 openid/unionid。

    WECHAT_MOCK=true 时不请求微信服务器，code 直接映射为固定 openid，
    便于本地开发与自动化测试。
    """
    if settings.wechat_mock:
        return {"openid": f"mock-{code}", "unionid": None}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            JSCODE2SESSION_URL,
            params={
                "appid": settings.wechat_appid,
                "secret": settings.wechat_secret,
                "js_code": code,
                "grant_type": "authorization_code",
            },
        )
        data = resp.json()
    if data.get("errcode"):
        raise BizError(f"微信登录失败：{data.get('errmsg', '未知错误')}", code=data["errcode"])
    return {"openid": data["openid"], "unionid": data.get("unionid")}
