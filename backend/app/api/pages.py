from fastapi import APIRouter

from app.deps import DB
from app.schemas.common import Resp
from app.services.pages import resolve_page

router = APIRouter()


@router.get("/pages/{key}", response_model=Resp[dict | None])
async def get_page(key: str, session: DB):
    """配置化页面（如 home）；data 为 None 时客户端使用默认写死排版。"""
    return Resp(data=await resolve_page(session, key))
