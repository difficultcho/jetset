from tests.conftest import login


async def test_login_and_me(client):
    headers = await login(client, "auth-user")
    resp = await client.get("/api/v1/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] > 0
    assert data["reco_enabled"] is True


async def test_login_same_code_same_user(client):
    h1 = await login(client, "repeat-user")
    h2 = await login(client, "repeat-user")
    r1 = await client.get("/api/v1/me", headers=h1)
    r2 = await client.get("/api/v1/me", headers=h2)
    assert r1.json()["data"]["id"] == r2.json()["data"]["id"]


async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == 401


async def test_update_me(client):
    headers = await login(client, "update-user")
    resp = await client.put("/api/v1/me", headers=headers, json={
        "name": "测试用户", "gender": "男", "birthday": "1990-01-01",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "测试用户"
    assert data["gender"] == "男"
