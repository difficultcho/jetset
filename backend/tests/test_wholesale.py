from tests.conftest import login


async def test_wholesale_apply(client):
    headers = await login(client, "ws-user")
    resp = await client.post("/api/v1/wholesale/applications", headers=headers, json={
        "type": "经销商", "phone": "15501147281", "company": "杭州某某贸易有限公司",
        "region": "浙江省 杭州市", "license_img": "/uploads/a.jpg", "store_img": "/uploads/b.jpg",
    })
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "pending"

    resp = await client.get("/api/v1/wholesale/applications/mine", headers=headers)
    assert len(resp.json()["data"]) == 1


async def test_wholesale_requires_images(client):
    headers = await login(client, "ws-user2")
    resp = await client.post("/api/v1/wholesale/applications", headers=headers, json={
        "type": "经销商", "phone": "15501147281", "company": "公司",
        "region": "", "license_img": "", "store_img": "",
    })
    assert resp.status_code == 422
