import logging
import time

import httpx

from app.config import settings
from app.errors import BizError

logger = logging.getLogger(__name__)

JSCODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
MSG_SEC_CHECK_URL = "https://api.weixin.qq.com/wxa/msg_sec_check"

_token_cache = {"value": "", "expires": 0.0}


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


async def _access_token() -> str | None:
    """获取并缓存接口调用凭据。失败返回 None（如服务器 IP 未加白名单）。"""
    now = time.time()
    if _token_cache["value"] and _token_cache["expires"] > now:
        return _token_cache["value"]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(ACCESS_TOKEN_URL, params={
                "grant_type": "client_credential",
                "appid": settings.wechat_appid,
                "secret": settings.wechat_secret,
            })
            data = resp.json()
    except Exception as e:
        logger.warning("获取 access_token 异常：%s", e)
        return None
    if "access_token" not in data:
        # 40164 = 服务器 IP 不在小程序后台白名单
        logger.warning("获取 access_token 失败：%s", data)
        return None
    _token_cache["value"] = data["access_token"]
    _token_cache["expires"] = now + data.get("expires_in", 7200) - 300
    return _token_cache["value"]


async def msg_sec_check(openid: str, content: str) -> str:
    """文本内容安全检测（昵称/备注等 UGC）。返回 pass/review/risky。

    mock 模式或检测服务不可用时降级放行（记日志），不阻塞业务功能。
    """
    if settings.wechat_mock or not content.strip():
        return "pass"
    token = await _access_token()
    if token is None:
        return "pass"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{MSG_SEC_CHECK_URL}?access_token={token}",
                json={"content": content, "version": 2, "scene": 1, "openid": openid},
            )
            data = resp.json()
    except Exception as e:
        logger.warning("msg_sec_check 异常，降级放行：%s", e)
        return "pass"
    if data.get("errcode") == 87014:  # 兼容旧错误码：内容违规
        return "risky"
    if data.get("errcode"):
        logger.warning("msg_sec_check 失败，降级放行：%s", data)
        return "pass"
    return data.get("result", {}).get("suggest", "pass")
