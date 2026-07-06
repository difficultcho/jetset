from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.admin import AdminUser
from app.models.user import User
from app.security import parse_token

DB = Annotated[AsyncSession, Depends(get_session)]


def _bearer(authorization: str | None) -> tuple[int, bool]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    parsed = parse_token(authorization[7:])
    if parsed is None:
        raise HTTPException(status_code=401, detail="登录已过期")
    return parsed


async def get_current_user(
    session: DB,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    uid, is_admin = _bearer(authorization)
    if is_admin:  # 管理端 token 不能用于 C 端接口
        raise HTTPException(status_code=401, detail="请使用用户身份登录")
    user = await session.get(User, uid)
    if user is None or user.status != 1:
        raise HTTPException(status_code=401, detail="账号不可用")
    return user


async def get_current_admin(
    session: DB,
    authorization: Annotated[str | None, Header()] = None,
) -> AdminUser:
    aid, is_admin = _bearer(authorization)
    if not is_admin:
        raise HTTPException(status_code=401, detail="需要管理员身份")
    admin = await session.get(AdminUser, aid)
    if admin is None or admin.status != 1:
        raise HTTPException(status_code=401, detail="管理员账号不可用")
    return admin


async def require_any_identity(
    session: DB,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """C 端用户或管理员均可（目前仅上传接口使用）。"""
    sid, is_admin = _bearer(authorization)
    row = await session.get(AdminUser if is_admin else User, sid)
    if row is None or row.status != 1:
        raise HTTPException(status_code=401, detail="账号不可用")


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[AdminUser, Depends(get_current_admin)]
