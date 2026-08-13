"""素材完整性核对：把库里引用到的所有素材路径收齐，逐个到对象存储确认存在。

在服务器上执行：
    docker compose exec api python -m scripts.check_assets

只读：不上传、不删除、不改库。用于迁移后确认没有漏网的引用。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.api.uploads import s3_client, s3_enabled  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import SessionFactory, engine  # noqa: E402
from app.models.catalog import SpuImage  # noqa: E402
from app.models.cms import Page  # noqa: E402
from app.models.shop import ShopMenu  # noqa: E402
from app.models.store import Store  # noqa: E402


def _walk(node, out: set) -> None:
    """从任意 JSON 结构里捞出 /uploads/ 开头的路径（块、图片跳链都是嵌套结构）。"""
    if isinstance(node, str):
        if node.startswith("/uploads/"):
            out.add(node)
    elif isinstance(node, dict):
        for v in node.values():
            _walk(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk(v, out)


async def collect() -> dict[str, set]:
    """按来源归类，方便定位问题出在哪张表。"""
    found: dict[str, set] = {}
    async with SessionFactory() as s:
        found["商品图 spu_image.url"] = {
            u for u in (await s.execute(select(SpuImage.url))).scalars() if u
        }
        pages: set = set()
        for p in (await s.execute(select(Page))).scalars():
            _walk(p.blocks, pages)
        found["页面 page.blocks"] = pages

        menus: set = set()
        for m in (await s.execute(select(ShopMenu))).scalars():
            _walk(m.banners, menus)
        found["商城图片跳链 shop_menu.banners"] = menus

        stores: set = set()
        for st in (await s.execute(select(Store))).scalars():
            _walk(st.images, stores)
            _walk(st.consultant_qr, stores)
        found["门店 store.images/qr"] = stores
    return found


def list_bucket(client) -> dict[str, int]:
    """列出桶里 uploads/ 下的全部对象 → {路径: 字节数}。分页取，别漏。"""
    out: dict[str, int] = {}
    token = None
    while True:
        kw = {"Bucket": settings.s3_bucket, "Prefix": "uploads/", "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        resp = client.list_objects_v2(**kw)
        for obj in resp.get("Contents", []):
            out["/" + obj["Key"]] = obj["Size"]
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return out


def exists_in_s3(client, path: str) -> bool:
    key = path.lstrip("/")  # /uploads/x.jpg → uploads/x.jpg
    try:
        client.head_object(Bucket=settings.s3_bucket, Key=key)
        return True
    except Exception:
        return False


async def main() -> None:
    if not s3_enabled():
        sys.exit("✗ S3_* 未配齐，无从核对")

    found = await collect()
    all_paths = set().union(*found.values()) if found else set()
    print(f"库里引用的素材共 {len(all_paths)} 个（去重后）\n")

    client = s3_client()
    missing_by_src: dict[str, list] = {}
    checked: dict[str, bool] = {}
    for src, paths in found.items():
        miss = []
        for p in sorted(paths):
            if p not in checked:
                checked[p] = exists_in_s3(client, p)
            if not checked[p]:
                miss.append(p)
        print(f"  {src:32} 引用 {len(paths):3} 个，缺失 {len(miss)}")
        if miss:
            missing_by_src[src] = miss

    # 本地还剩什么（迁移脚本不删本地文件，这里看看是否已全部有对应对象）
    local = Path(settings.upload_dir)
    local_files = sorted(f.name for f in local.iterdir() if f.is_file()) if local.is_dir() else []
    orphan_local = [n for n in local_files if not exists_in_s3(client, f"/uploads/{n}")]

    print(f"\n本地目录 {local} 还有 {len(local_files)} 个文件，其中 {len(orphan_local)} 个在对象存储里找不到")

    if missing_by_src:
        print("\n✗ 以下引用在对象存储里不存在（小程序上会裂图）：")
        for src, miss in missing_by_src.items():
            print(f"  [{src}]")
            for p in miss[:20]:
                print(f"    {p}" + ("   ← 本地还有，重跑迁移即可"
                                    if p.split("/")[-1] in local_files else "   ← 本地也没有，源文件已丢"))
            if len(miss) > 20:
                print(f"    …… 另有 {len(miss) - 20} 个")
    else:
        print("\n✓ 库里引用的素材在对象存储中全部存在")
    # 反方向：桶里有、库里没人引用的对象。
    # 主要来源是"上传成功但保存失败"——图片点上传时就进桶了，页面保存是后一步，
    # 保存报错时文件已经躺在桶里，没有任何记录指向它。
    print("\n=== 桶里没人引用的对象 ===")
    try:
        in_bucket = list_bucket(client)
    except Exception as e:
        print(f"  列举失败（{type(e).__name__}），跳过：{e}")
        in_bucket = {}
    if in_bucket:
        orphans = {k: v for k, v in in_bucket.items() if k not in all_paths}
        mb = sum(orphans.values()) / 1024 / 1024
        print(f"  桶内共 {len(in_bucket)} 个对象，其中 {len(orphans)} 个没人引用（{mb:.1f} MB）")
        for k in sorted(orphans)[:30]:
            print(f"    {k}  {orphans[k] // 1024} KB")
        if len(orphans) > 30:
            print(f"    …… 另有 {len(orphans) - 30} 个")
        if orphans:
            print("\n  这些是安全可删的：库里任何商品/页面/系列/门店都没指向它们。")
            print("  但删之前请确认没有正在编辑、尚未保存的内容。")

    if orphan_local:
        print(f"\n△ 本地有但没传上去的 {len(orphan_local)} 个（可能是没被引用的历史文件）：")
        for n in orphan_local[:10]:
            print(f"    {n}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
