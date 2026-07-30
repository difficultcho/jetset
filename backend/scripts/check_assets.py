"""素材完整性核对：把库里引用到的所有素材路径收齐，逐个到对象存储确认存在。

在服务器上执行：
    docker compose exec api python -m scripts.check_assets

只读：不上传、不删除、不改库。用于迁移后确认没有漏网的引用。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, select  # noqa: E402

from app.api.uploads import s3_client, s3_enabled  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import SessionFactory, engine  # noqa: E402
from app.models.catalog import SpuImage  # noqa: E402
from app.models.cms import Page  # noqa: E402
from app.models.series import Series  # noqa: E402
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
        found["系列封面 series.cover"] = {
            c for c in (await s.execute(select(Series.cover))).scalars() if c
        }
        pages: set = set()
        for p in (await s.execute(select(Page))).scalars():
            _walk(p.cover, pages)
            _walk(p.blocks, pages)
        found["页面 page.cover/blocks"] = pages

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
    if orphan_local:
        print(f"\n△ 本地有但没传上去的 {len(orphan_local)} 个（可能是没被引用的历史文件）：")
        for n in orphan_local[:10]:
            print(f"    {n}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
