"""首页视频位：配置系列 → /home 播该系列内容帖的第一个视频。"""
from tests.test_admin import admin_login


async def test_home_video_slot(client):
    h = await admin_login(client)
    s = (await client.post("/api/admin/series", headers=h, json={
        "name": "视频位测试系列", "en": "VIDEO SLOT", "sort": 99})).json()["data"]
    sid = s["id"]

    # 系列没有任何关联内容帖 → 配置被拒，报错指向「关联」
    resp = await client.put("/api/admin/home-video", headers=h, json={"series_id": sid})
    assert resp.status_code == 400
    assert "关联" in resp.json()["message"]

    # 挂了帖但帖里没有视频块 → 配置被拒，报错指向「视频块」
    post = (await client.post("/api/admin/brand/posts", headers=h, json={
        "type": "campaign", "title": "VIDEO SLOT 大片", "series_id": sid,
        "body": [{"kind": "image", "img": "/uploads/a.jpg"}],
        "sort": 99})).json()["data"]
    resp = await client.put("/api/admin/home-video", headers=h, json={"series_id": sid})
    assert resp.status_code == 400
    assert "视频块" in resp.json()["message"]

    # 补上视频块（在图片块之后，仍应被选中）→ 配置成功
    post["body"] = [{"kind": "image", "img": "/uploads/a.jpg"},
                    {"kind": "video", "src": "/uploads/slot.mp4", "poster": "/uploads/p.jpg"}]
    await client.put(f"/api/admin/brand/posts/{post['id']}", headers=h, json=post)
    resp = await client.put("/api/admin/home-video", headers=h, json={"series_id": sid})
    assert resp.status_code == 200
    state = resp.json()["data"]
    assert state["series_id"] == sid and state["video"]["src"] == "/uploads/slot.mp4"

    # C 端 /home 返回解析后的视频与系列信息
    v = (await client.get("/api/v1/home")).json()["data"]["video"]
    assert v["src"] == "/uploads/slot.mp4" and v["poster"] == "/uploads/p.jpg"
    assert v["post_id"] == post["id"] and v["series_en"] == "VIDEO SLOT"

    # 帖子下架 → 视频位静默消失（配置仍在，不报错）
    post["status"] = 0
    await client.put(f"/api/admin/brand/posts/{post['id']}", headers=h, json=post)
    assert (await client.get("/api/v1/home")).json()["data"]["video"] is None

    # 清除配置 + 收尾下架系列，不影响其他用例
    resp = await client.put("/api/admin/home-video", headers=h, json={"series_id": 0})
    assert resp.status_code == 200 and resp.json()["data"]["series_id"] == 0
    s["status"] = 0
    await client.put(f"/api/admin/series/{sid}", headers=h, json=s)
    assert (await client.get("/api/v1/home")).json()["data"]["video"] is None
