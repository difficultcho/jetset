from fastapi import APIRouter
from sqlalchemy import select

from app.deps import DB
from app.models.user import User
from app.schemas.common import Resp
from app.schemas.user import LoginData, LoginReq, UserOut
from app.security import create_token
from app.services import coupons as coupon_svc
from app.services.wechat import code2session

router = APIRouter()


@router.post("/auth/login", response_model=Resp[LoginData])
async def login(req: LoginReq, session: DB):
    wx = await code2session(req.code)
    user = (
        await session.execute(select(User).where(User.openid == wx["openid"]))
    ).scalar_one_or_none()
    new_coupons = 0
    if user is None:
        # 静默注册：openid 即账号
        user = User(openid=wx["openid"], unionid=wx.get("unionid"))
        session.add(user)
        await session.flush()
        new_coupons = len(await coupon_svc.grant_newcomer_coupons(session, user))
        await session.commit()
    return Resp(data=LoginData(
        token=create_token(user.id),
        user=UserOut.model_validate(user),
        new_coupons=new_coupons,
    ))
