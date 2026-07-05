from fastapi import APIRouter

from app.deps import DB, CurrentUser
from app.schemas.common import Resp
from app.schemas.user import UserOut, UserUpdate

router = APIRouter()


@router.get("/me", response_model=Resp[UserOut])
async def get_me(user: CurrentUser):
    return Resp(data=UserOut.model_validate(user))


@router.put("/me", response_model=Resp[UserOut])
async def update_me(req: UserUpdate, user: CurrentUser, session: DB):
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await session.commit()
    return Resp(data=UserOut.model_validate(user))
