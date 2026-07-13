"""素材批量导入：上传图片到线上并挂载到 首页轮播 / 广告大片。

用法（在 backend/ 下）：
    .venv/bin/python scripts/import_assets.py <素材目录>

环境变量：
    JETSET_BASE     默认 https://bce.kkmsee.com/jetset
    ADMIN_USER      默认 admin
    ADMIN_PASSWORD  默认 jetset-admin

按文件名约定挂载（可重复执行，同名标题不重复创建）：
    hero_*      → 首页轮播 Banner（一张一条）
    campaign_*  → 「MID SEASON SALE」广告大片首图（宽幅）
    midseason_* → 同上，第二块
    其余         → 仅上传，打印 URL 供后台手工挂载（如商品图）
"""
import mimetypes
import os
import sys
from pathlib import Path

import httpx

BASE = os.environ.get("JETSET_BASE", "https://bce.kkmsee.com/jetset")
TIMEOUT = httpx.Timeout(300, connect=15)  # 大图慢链路，上传超时放宽到 5 分钟


def unwrap(resp: httpx.Response) -> dict | list | None:
    resp.raise_for_status()
    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(f"{resp.request.url}: {body.get('message')}")
    return body.get("data")


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    asset_dir = Path(sys.argv[1])
    files = sorted(p for p in asset_dir.iterdir()
                   if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    if not files:
        sys.exit(f"目录中没有图片：{asset_dir}")

    # trust_env=False：忽略 shell 的代理环境变量（国内服务器直连更稳）
    client = httpx.Client(base_url=BASE, timeout=TIMEOUT, trust_env=False)

    login = client.post("/api/admin/auth/login", json={
        "username": os.environ.get("ADMIN_USER", "admin"),
        "password": os.environ.get("ADMIN_PASSWORD", "jetset-admin"),
    })
    if login.status_code == 401:
        sys.exit("✗ 管理员账号/密码错误：请带 ADMIN_PASSWORD=<你的密码> 重新运行")
    token = unwrap(login)["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    print(f"✓ 登录成功：{BASE}")

    # 1) 全部上传
    urls: dict[str, str] = {}
    for f in files:
        mime = mimetypes.guess_type(f.name)[0] or "image/jpeg"
        with f.open("rb") as fh:
            data = unwrap(client.post("/api/v1/uploads", files={"file": (f.name, fh, mime)}))
        urls[f.name] = data["url"]
        print(f"✓ 上传 {f.name} ({f.stat().st_size // 1024}KB) → {data['url']}")

    # 2) hero_* → 首页轮播（标题取文件名，已存在同名则跳过）
    banners = unwrap(client.get("/api/admin/banners"))
    for name, url in urls.items():
        if not name.startswith("hero_"):
            continue
        title = Path(name).stem.replace("hero_", "").replace("_", " ").upper()
        if any(b["title"] == title for b in banners):
            print(f"- 轮播「{title}」已存在，跳过")
            continue
        unwrap(client.post("/api/admin/banners", json={
            "title": title, "sub_title": "", "image": url, "link": "",
            "sort": len(banners), "status": 1,
        }))
        print(f"✓ 新建轮播「{title}」")

    # 3) campaign_* / midseason_* → 广告大片（sort=-1 排到最前，成为 C 端展示的那一篇）
    wide = next((u for n, u in urls.items() if n.startswith("campaign_")), None)
    second = next((u for n, u in urls.items() if n.startswith("midseason_")), None)
    if wide:
        posts = unwrap(client.get("/api/admin/brand/posts", params={"type": "campaign"}))
        if any(p["title"] == "MID SEASON SALE" for p in posts):
            print("- 广告大片「MID SEASON SALE」已存在，跳过")
        else:
            body = [{"kind": "image", "img": wide, "ratio": "15/8", "inset": False,
                     "ph": "", "tint": "#e6ddce"}]
            if second:
                body.append({"kind": "image", "img": second, "ratio": "16/9", "inset": True,
                             "ph": "", "tint": "#e6ddce"})
            unwrap(client.post("/api/admin/brand/posts", json={
                "type": "campaign", "title": "MID SEASON SALE", "subtitle": "季中特惠",
                "cover": wide, "cover_tint": "#e6ddce", "body": body, "link": "",
                "sort": -1, "status": 1,
            }))
            print("✓ 新建广告大片「MID SEASON SALE」（2 个图块，排在最前）")

    # 4) 现状汇总
    print("\n—— 线上现状 ——")
    for b in unwrap(client.get("/api/admin/banners")):
        print(f"轮播 #{b['id']} 「{b['title']}」 图片={'有' if b['image'] else '无'} "
              f"启用={'是' if b['status'] == 1 else '否'} 排序={b['sort']}")
    for p in unwrap(client.get("/api/admin/brand/posts", params={"type": "campaign"})):
        print(f"大片 #{p['id']} 「{p['title']}」 图块={len(p['body'])} 排序={p['sort']}")
    spare = {n: u for n, u in urls.items()
             if not n.startswith(("hero_", "campaign_", "midseason_"))}
    if spare:
        print("\n未自动挂载（商品图等，后台商品编辑里选用）：")
        for n, u in spare.items():
            print(f"  {n} → {u}")


if __name__ == "__main__":
    main()
