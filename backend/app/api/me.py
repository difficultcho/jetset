from fastapi import APIRouter

from app.deps import DB, CurrentUser
from app.errors import BizError
from app.schemas.common import Resp
from app.schemas.user import UserOut, UserUpdate
from app.services import wechat

router = APIRouter()


@router.get("/me", response_model=Resp[UserOut])
async def get_me(user: CurrentUser):
    return Resp(data=UserOut.model_validate(user))


@router.put("/me", response_model=Resp[UserOut])
async def update_me(req: UserUpdate, user: CurrentUser, session: DB):
    # 昵称属 UGC，过微信内容安全检测（risky 拒绝，review 放行留日志）
    if req.name and req.name != user.name:
        if await wechat.msg_sec_check(user.openid, req.name) == "risky":
            raise BizError("昵称包含违规内容，请修改")
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await session.commit()
    return Resp(data=UserOut.model_validate(user))
