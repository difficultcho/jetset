"""把 FW26/27 棚拍按款号建档到线上。

用法（在仓库根目录或 backend/ 下均可）：
    backend/.venv/bin/python backend/scripts/import_fw2627_packshots.py --reset

--reset 会先删除全部现有商品（订单快照保留），再上传。
中途失败后去掉 --reset 再跑：已有的 10 位款号会跳过。

管理员账号读 backend/.env，不打印密码。
图片用 display/ 里的 JPEG。颜色名按下表，颜色编码是目录上的 4 位数字。
"""
import json
import mimetypes
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / "backend" / ".env"
DISPLAY = ROOT / "assets/from Switzerland/Packshots Collection 26-27/display"
CACHE = Path("/tmp/jetset-fw2627-upload.json")
BASE = os.environ.get("JETSET_BASE", "https://bce.kkmsee.com/jetset")
TIMEOUT = httpx.Timeout(120, connect=20)

COLOR_NAMES = {
    "9055": "黑色",
    "5101": "静暮灰紫",
    "6009": "薄荷绿",
    "0052": "鼠尾草绿",
    "3015": "灵蛇白",
    "7002": "红色",
    "6007": "深蓝色",
    "0980": "酒红色",
    "8000": "奶油白",
    "4015": "烟熏黑",
    "9001": "灰色",
    "6016": "紫色",
    "3014": "灵蛇黑",
    "0093": "深灰色",
    "3100": "烟灰色",
    "7003": "芥末黄",
    "7071": "沙色蟒纹",
    "8227": "绿红幻彩",
}
SIZES = ["S", "M", "L", "XL"]
PRICE = 1_000_000  # 10000 元
VIEWS = ["front.jpg", "back.jpg", "detail-1.jpg", "detail-2.jpg", "detail-3.jpg", "detail-4.jpg"]


def load_env() -> None:
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def unwrap(resp: httpx.Response):
    if resp.status_code >= 400:
        raise RuntimeError(f"{resp.request.method} {resp.request.url} -> {resp.status_code} {resp.text[:400]}")
    body = resp.json()
    if body.get("code") != 0:
        raise RuntimeError(f"{resp.request.url}: {body.get('message')}")
    return body.get("data")


def styles() -> list[tuple[str, list[tuple[str, Path]]]]:
    found = []
    unknown = set()
    for style_dir in sorted(p for p in DISPLAY.iterdir() if p.is_dir()):
        colors = []
        for color_dir in sorted(p for p in style_dir.iterdir() if p.is_dir()):
            code = color_dir.name
            if code not in COLOR_NAMES:
                unknown.add(code)
            if not (color_dir / "front.jpg").is_file():
                raise SystemExit(f"缺少正面图：{style_dir.name}/{code}")
            colors.append((code, color_dir))
        found.append((style_dir.name, colors))
    if unknown:
        raise SystemExit(f"没有中文名的颜色编码：{sorted(unknown)}")
    return found


def main() -> None:
    reset = "--reset" in sys.argv
    load_env()
    catalog = styles()
    style_codes = {code for code, _ in catalog}
    print(f"本地 {len(catalog)} 个款号，{sum(len(c) for _, c in catalog)} 个颜色")

    client = httpx.Client(base_url=BASE, timeout=TIMEOUT, trust_env=False)
    spec = client.get("/openapi.json")
    spec.raise_for_status()
    if "color_code" not in spec.text:
        raise SystemExit("线上接口还没有颜色编码字段。先等后端部署完成再跑。")

    login = client.post("/api/admin/auth/login", json={
        "username": os.environ.get("ADMIN_USERNAME", "admin"),
        "password": os.environ["ADMIN_PASSWORD"],
    })
    if login.status_code == 401:
        raise SystemExit("管理员账号或密码不正确")
    client.headers["Authorization"] = "Bearer " + unwrap(login)["token"]
    print(f"已登录 {BASE}")

    cats = unwrap(client.get("/api/admin/categories"))
    named = [c for c in cats if c["name"] == "滑雪裤"]
    if len(named) != 1:
        raise SystemExit(f"需要恰好一个品类「滑雪裤」，实际 {[c['id'] for c in named]}")
    category_id = named[0]["id"]
    print(f"品类「滑雪裤」id={category_id}")

    def all_products() -> list[dict]:
        items, page = [], 1
        while True:
            data = unwrap(client.get("/api/admin/products", params={"page": page, "page_size": 100}))
            items.extend(data["items"])
            if len(items) >= data["total"]:
                return items
            page += 1

    if reset:
        existing = all_products()
        print(f"删除现有商品 {len(existing)} 个")
        for item in existing:
            unwrap(client.delete(f"/api/admin/products/{item['id']}"))
        left = unwrap(client.get("/api/admin/products", params={"page_size": 1}))["total"]
        if left != 0:
            raise SystemExit(f"清空后仍有 {left} 个商品")
        print("商品已清空")

    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {"images": {}}
    have = {item["code"] for item in all_products()}

    def upload(path: Path) -> str:
        key = str(path.relative_to(DISPLAY))
        cached = cache["images"].get(key)
        if cached:
            return cached
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        with path.open("rb") as fh:
            url = unwrap(client.post("/api/v1/uploads", files={"file": (path.name, fh, mime)}))["url"]
        cache["images"][key] = url
        CACHE.write_text(json.dumps(cache))
        return url

    for style, colors in catalog:
        if style in have:
            print(f"- {style} 已存在，跳过")
            continue
        skus, images = [], []
        for index, (color_code, folder) in enumerate(colors):
            for size in SIZES:
                skus.append({
                    "color_index": index,
                    "color_name": COLOR_NAMES[color_code],
                    "color_code": color_code,
                    "color_hex": "#888888",
                    "size": size,
                    "price": PRICE,
                    "stock": 1,
                    "status": 1,
                })
            for name in VIEWS:
                file = folder / name
                if not file.is_file():
                    continue
                images.append({"color_index": index, "url": upload(file), "sort": len(images)})
        unwrap(client.post("/api/admin/products", json={
            "category_id": category_id,
            "name": style,
            "code": style,
            "status": 1,
            "sellable": True,
            "skus": skus,
            "images": images,
        }))
        print(f"✓ {style}  {len(colors)} 色 / {len(skus)} SKU / {len(images)} 图")

    missing = style_codes - {item["code"] for item in all_products()}
    if missing:
        raise SystemExit(f"仍缺款号：{sorted(missing)}")
    print(f"完成，线上商品 {unwrap(client.get('/api/admin/products', params={'page_size': 1}))['total']} 个")


if __name__ == "__main__":
    main()
