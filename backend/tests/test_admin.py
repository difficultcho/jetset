from tests.conftest import login


async def admin_login(client) -> dict:
    resp = await client.post("/api/admin/auth/login",
                             json={"username": "admin", "password": "jetset-admin"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": "Bearer " + resp.json()["data"]["token"]}


async def test_admin_login_wrong_password(client):
    resp = await client.post("/api/admin/auth/login",
                             json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


async def test_token_isolation(client):
    admin_h = await admin_login(client)
    user_h = await login(client, "adm-iso")
    # 管理员 token 不能调 C 端接口
    resp = await client.get("/api/v1/me", headers=admin_h)
    assert resp.status_code == 401
    # 用户 token 不能调管理接口
    resp = await client.get("/api/admin/stats", headers=user_h)
    assert resp.status_code == 401


async def test_product_crud(client):
    h = await admin_login(client)

    # 创建商品：2 色 × 2 码
    payload = {
        "category_id": 1, "name": "测试冲锋衣", "en_model": "TEST-X 1.0",
        "brief": "简介", "detail": "详情", "badge": None, "featured": False,
        "sort": 99, "status": 1,
        "skus": [
            {"color_index": 0, "color_name": "黑", "color_hex": "#111111", "size": "M", "price": 10000, "stock": 5},
            {"color_index": 0, "color_name": "黑", "color_hex": "#111111", "size": "L", "price": 10000, "stock": 5},
            {"color_index": 1, "color_name": "白", "color_hex": "#eeeeee", "size": "M", "price": 12000, "stock": 3},
            {"color_index": 1, "color_name": "白", "color_hex": "#eeeeee", "size": "L", "price": 12000, "stock": 3}
        ],
        "images": [{"color_index": 0, "url": "/uploads/a.jpg", "sort": 0}]
    }
    resp = await client.post("/api/admin/products", headers=h, json=payload)
    assert resp.status_code == 200, resp.text
    spu_id = resp.json()["data"]["id"]

    # 展示价 = 最低 SKU 价
    detail = (await client.get(f"/api/admin/products/{spu_id}", headers=h)).json()["data"]
    assert detail["price"] == 10000
    assert len(detail["skus"]) == 4
    assert len(detail["images"]) == 1

    # 更新：去掉白色 L 码（应停售而非删除）、改价、换图
    payload["skus"] = [s for s in payload["skus"] if not (s["color_index"] == 1 and s["size"] == "L")]
    payload["skus"][0]["price"] = 9000
    payload["images"] = [{"color_index": 1, "url": "/uploads/b.jpg", "sort": 0}]
    resp = await client.put(f"/api/admin/products/{spu_id}", headers=h, json=payload)
    assert resp.status_code == 200

    detail = (await client.get(f"/api/admin/products/{spu_id}", headers=h)).json()["data"]
    assert detail["price"] == 9000
    off = [s for s in detail["skus"] if s["status"] == 0]
    assert len(off) == 1 and off[0]["size"] == "L" and off[0]["color_index"] == 1
    assert detail["images"][0]["url"] == "/uploads/b.jpg"

    # C 端能看到该商品（status=1），下架后消失
    resp = await client.get(f"/api/v1/products/{spu_id}")
    assert resp.status_code == 200
    await client.post(f"/api/admin/products/{spu_id}/status", headers=h, json={"status": 0})
    resp = await client.get(f"/api/v1/products/{spu_id}")
    assert resp.status_code == 404

    # 管理端列表能按状态筛出
    page = (await client.get("/api/admin/products", headers=h, params={"status": 0})).json()["data"]
    assert any(p["id"] == spu_id for p in page["items"])


async def test_ship_flow(client):
    admin_h = await admin_login(client)
    user_h = await login(client, "adm-ship")

    # 用户下单并支付
    addr = await client.post("/api/v1/addresses", headers=user_h, json={
        "name": "发货测试", "phone": "13900000000", "region": "", "detail": "路 1 号"})
    listing = await client.get("/api/v1/products", params={"q": "手套"})
    spu_id = listing.json()["data"]["items"][0]["id"]
    sku = (await client.get(f"/api/v1/products/{spu_id}")).json()["data"]["skus"][0]
    order = (await client.post("/api/v1/orders", headers=user_h, json={
        "items": [{"sku_id": sku["id"], "qty": 1}],
        "address_id": addr.json()["data"]["id"]})).json()["data"]
    await client.post("/api/v1/payments/mock/confirm", json={"order_no": order["order_no"]})

    # 未发货前不能确认收货；不能对待发货以外的单发货
    resp = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=user_h)
    assert resp.status_code == 400

    # 管理员发货
    resp = await client.post(f"/api/admin/orders/{order['id']}/ship", headers=admin_h,
                             json={"company": "顺丰", "tracking_no": "SF123456"})
    assert resp.json()["data"]["status"] == "pending_receipt"

    # 重复发货被拒
    resp = await client.post(f"/api/admin/orders/{order['id']}/ship", headers=admin_h,
                             json={"company": "顺丰", "tracking_no": "SF999"})
    assert resp.status_code == 400

    # C 端订单详情能看到物流
    detail = (await client.get(f"/api/v1/orders/{order['id']}", headers=user_h)).json()["data"]
    assert detail["shipment"]["tracking_no"] == "SF123456"

    # 用户确认收货 → 待评价
    resp = await client.post(f"/api/v1/orders/{order['id']}/confirm", headers=user_h)
    assert resp.json()["data"]["status"] == "pending_review"


async def test_wholesale_review(client):
    admin_h = await admin_login(client)
    user_h = await login(client, "adm-ws")
    await client.post("/api/v1/wholesale/applications", headers=user_h, json={
        "type": "经销商", "phone": "15500000000", "company": "审核测试公司",
        "region": "浙江省", "license_img": "/uploads/l.jpg", "store_img": "/uploads/s.jpg"})

    page = (await client.get("/api/admin/wholesale", headers=admin_h,
                             params={"status": "pending"})).json()["data"]
    app_id = next(a["id"] for a in page["items"] if a["company"] == "审核测试公司")

    resp = await client.post(f"/api/admin/wholesale/{app_id}/review", headers=admin_h,
                             json={"action": "approve", "note": "资质齐全"})
    assert resp.json()["data"]["status"] == "approved"

    # 重复审核被拒
    resp = await client.post(f"/api/admin/wholesale/{app_id}/review", headers=admin_h,
                             json={"action": "reject"})
    assert resp.status_code == 400

    # 申请人能看到结果
    mine = (await client.get("/api/v1/wholesale/applications/mine", headers=user_h)).json()["data"]
    assert mine[0]["status"] == "approved"


async def test_banner_crud_and_home(client):
    h = await admin_login(client)
    created = (await client.post("/api/admin/banners", headers=h, json={
        "title": "测试轮播", "sub_title": "TEST", "sort": 9})).json()["data"]

    home = (await client.get("/api/v1/home")).json()["data"]
    assert any(b["title"] == "测试轮播" for b in home["banners"])

    await client.put(f"/api/admin/banners/{created['id']}", headers=h, json={
        "title": "测试轮播", "sub_title": "TEST", "sort": 9, "status": 0})
    home = (await client.get("/api/v1/home")).json()["data"]
    assert not any(b["title"] == "测试轮播" for b in home["banners"])

    resp = await client.delete(f"/api/admin/banners/{created['id']}", headers=h)
    assert resp.status_code == 200


async def test_change_password(client):
    h = await admin_login(client)
    # 原密码错误被拒
    resp = await client.post("/api/admin/auth/password", headers=h,
                             json={"old_password": "wrong", "new_password": "new-password-123"})
    assert resp.status_code == 400
    # 修改成功后新密码可登录，旧密码失效
    resp = await client.post("/api/admin/auth/password", headers=h,
                             json={"old_password": "jetset-admin", "new_password": "new-password-123"})
    assert resp.status_code == 200
    resp = await client.post("/api/admin/auth/login",
                             json={"username": "admin", "password": "jetset-admin"})
    assert resp.status_code == 401
    resp = await client.post("/api/admin/auth/login",
                             json={"username": "admin", "password": "new-password-123"})
    assert resp.status_code == 200
    # 改回去，避免影响其他用例
    h2 = {"Authorization": "Bearer " + resp.json()["data"]["token"]}
    await client.post("/api/admin/auth/password", headers=h2,
                      json={"old_password": "new-password-123", "new_password": "jetset-admin"})


async def test_stats(client):
    h = await admin_login(client)
    data = (await client.get("/api/admin/stats", headers=h)).json()["data"]
    assert data["users"] >= 1
    assert data["products_on"] >= 1
    assert "gmv_24h" in data and "pending_shipment" in data
