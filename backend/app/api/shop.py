from fastapi import APIRouter

from app.deps import DB
from app.schemas.common import Resp
from app.services.shop import resolve_shop

router = APIRouter()


@router.get("/shop", response_model=Resp[dict])
async def shop(session: DB):
    """商城骨架：左菜单 + 每项的图片跳链与下钻入口。"""
    return Resp(data=await resolve_shop(session))
