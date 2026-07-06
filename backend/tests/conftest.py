import asyncio
import os
import tempfile

# 必须在导入 app 之前设置环境（settings 为模块级单例）
_tmp = tempfile.mkdtemp(prefix="jetset-test-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ["AUTO_CREATE_TABLES"] = "false"
os.environ["WECHAT_MOCK"] = "true"
os.environ["PAYMENT_PROVIDER"] = "mock"
os.environ["JWT_SECRET"] = "test-secret-0123456789abcdef0123456789abcdef"
os.environ["UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["FREIGHT_CENTS"] = "0"

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import SessionFactory, create_all
from app.main import app
from app.seed import ensure_admin, seed_all


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    async def _setup():
        await create_all()
        async with SessionFactory() as session:
            await seed_all(session)
            await ensure_admin(session)
            await session.commit()

    asyncio.run(_setup())


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def login(client: AsyncClient, code: str = "user1") -> dict:
    """mock 登录，返回带 token 的请求头。"""
    resp = await client.post("/api/v1/auth/login", json={"code": code})
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}
