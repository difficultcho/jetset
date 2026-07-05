from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.user import User
from app.security import parse_token

DB = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: DB,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    user_id = parse_token(authorization[7:])
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已过期")
    user = await session.get(User, user_id)
    if user is None or user.status != 1:
        raise HTTPException(status_code=401, detail="账号不可用")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
