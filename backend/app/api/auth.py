from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB
from app.models.user import User
from app.schemas.common import Resp
from app.schemas.user import LoginData, LoginReq, UserOut
from app.security import create_token
from app.services.wechat import code2session

router = APIRouter()


@router.post("/auth/login", response_model=Resp[LoginData])
async def login(req: LoginReq, session: DB):
    wx = await code2session(req.code)
    user = (
        await session.execute(select(User).where(User.openid == wx["openid"]))
    ).scalar_one_or_none()
    if user is None:
        user = User(openid=wx["openid"], unionid=wx.get("unionid"))
        session.add(user)
        await session.commit()
    return Resp(data=LoginData(token=create_token(user.id), user=UserOut.model_validate(user)))
