from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.deps import DB, CurrentAdmin
from app.models.admin import AdminUser
from app.schemas.admin import AdminLoginReq
from app.schemas.common import Resp
from app.security import create_token, hash_password, verify_password

router = APIRouter()


class ChangePasswordReq(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/auth/login", response_model=Resp[dict])
async def login(req: AdminLoginReq, session: DB):
    admin = (
        await session.execute(select(AdminUser).where(AdminUser.username == req.username))
    ).scalar_one_or_none()
    if admin is None or admin.status != 1 or not verify_password(req.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return Resp(data={"token": create_token(admin.id, admin=True), "username": admin.username})


@router.get("/auth/me", response_model=Resp[dict])
async def me(admin: CurrentAdmin):
    return Resp(data={"id": admin.id, "username": admin.username})


@router.post("/auth/password", response_model=Resp[None])
async def change_password(req: ChangePasswordReq, admin: CurrentAdmin, session: DB):
    if not verify_password(req.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    admin.password_hash = hash_password(req.new_password)
    await session.commit()
    return Resp()
