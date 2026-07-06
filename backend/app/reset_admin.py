"""把管理员密码重置为当前 ADMIN_PASSWORD 环境变量的值（账号不存在则创建）。

用法: python -m app.reset_admin
适用场景：忘记密码 / seed 后才修改 .env 的 ADMIN_PASSWORD 导致对不上。
"""

import asyncio

from sqlalchemy import select

from app.config import settings
from app.db import SessionFactory, create_all, engine
from app.models.admin import AdminUser
from app.security import hash_password


async def main() -> None:
    await create_all()
    async with SessionFactory() as session:
        admin = (
            await session.execute(
                select(AdminUser).where(AdminUser.username == settings.admin_username)
            )
        ).scalar_one_or_none()
        if admin:
            admin.password_hash = hash_password(settings.admin_password)
            action = "updated"
        else:
            session.add(AdminUser(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
            ))
            action = "created"
        await session.commit()
    await engine.dispose()
    print(f"admin '{settings.admin_username}' {action}，密码已设为 ADMIN_PASSWORD 的当前值")


if __name__ == "__main__":
    asyncio.run(main())
