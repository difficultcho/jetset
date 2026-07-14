from tests.conftest import login

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffff3f0300050001a5f645400000000049454e44ae426082"
)


async def test_upload_and_serve(client):
    headers = await login(client, "upload-user")
    resp = await client.post(
        "/api/v1/uploads", headers=headers,
        files={"file": ("a.png", PNG_1PX, "image/png")},
    )
    assert resp.status_code == 200, resp.text
    url = resp.json()["data"]["url"]
    assert url.startswith("/uploads/")

    # 上传后的文件可通过返回的 URL 访问
    resp = await client.get(url)
    assert resp.status_code == 200
    assert resp.content == PNG_1PX


async def test_upload_requires_auth(client):
    resp = await client.post("/api/v1/uploads", files={"file": ("a.png", PNG_1PX, "image/png")})
    assert resp.status_code == 401


async def test_upload_video_mp4(client):
    headers = await login(client, "upload-user3")
    fake_mp4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64
    resp = await client.post(
        "/api/v1/uploads", headers=headers,
        files={"file": ("clip.mp4", fake_mp4, "video/mp4")},
    )
    assert resp.status_code == 200, resp.text
    url = resp.json()["data"]["url"]
    assert url.endswith(".mp4")
    resp = await client.get(url)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("video/mp4")


async def test_upload_rejects_non_image(client):
    headers = await login(client, "upload-user2")
    resp = await client.post(
        "/api/v1/uploads", headers=headers,
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


async def test_serve_upload_path_traversal_blocked(client):
    resp = await client.get("/uploads/..%2Fapp%2Fconfig.py")
    assert resp.status_code == 404
