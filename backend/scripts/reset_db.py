"""线上环境归零：清空数据库 + 清空对象存储里的素材，回到全新状态重新配置。

**不可逆。** 会删掉：所有配置（页面/商城菜单）、商品与品类、门店、
用户与其购物车/订单/地址/优惠券/积分，以及对象存储 uploads/ 下的全部素材。

在服务器上执行（库名与桶名都要显式写对，两者分别是各自的确认）：

    # 只清库，保留素材
    docker compose exec api python -m scripts.reset_db --confirm jetset

    # 库 + 对象存储一起清（从头上传配置用这个）
    docker compose exec api python -m scripts.reset_db --confirm jetset --purge-assets <桶名>

可选：
    --seed   重建后灌入演示数据（商品/门店/示例页面）。不加则只有空表 + 管理员账号。

执行顺序是先库后素材：万一素材清理中断，剩下的只是孤儿文件（无害）；
反过来则会留下一堆指向已删文件的记录（裂图）。

不会动：.env、Redis、管理员账号（会按 .env 里的用户名密码重建）。
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect, text  # noqa: E402

from app import models  # noqa: F401,E402  确保模型全部注册
from app.api.uploads import s3_client, s3_enabled  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import Base, SessionFactory, engine  # noqa: E402
from app.seed import ensure_admin, seed_all  # noqa: E402


async def drop_everything() -> list[str]:
    """删掉库里所有表——含已不在模型里的历史遗留表，确保是真正的干净库。"""
    async with engine.begin() as conn:
        names = await conn.run_sync(lambda c: inspect(c).get_table_names())
        if not names:
            return []
        # 外键互相引用，逐个 DROP 会因顺序失败；先关掉约束检查
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for t in names:
            await conn.execute(text(f"DROP TABLE IF EXISTS `{t}`"))
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    return names


def purge_assets(bucket: str) -> tuple[int, int]:
    """清空对象存储 uploads/ 前缀下的全部对象。返回 (删除数, 失败数)。"""
    client = s3_client()
    deleted = failed = 0
    token = None
    while True:
        kw = {"Bucket": bucket, "Prefix": "uploads/", "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        resp = client.list_objects_v2(**kw)
        keys = [{"Key": o["Key"]} for o in resp.get("Contents", [])]
        if keys:
            try:
                r = client.delete_objects(Bucket=bucket, Delete={"Objects": keys, "Quiet": True})
                failed += len(r.get("Errors", []))
                deleted += len(keys) - len(r.get("Errors", []))
            except Exception:
                # 部分 S3 兼容实现不支持批量删除，退化为逐个删
                for k in keys:
                    try:
                        client.delete_object(Bucket=bucket, Key=k["Key"])
                        deleted += 1
                    except Exception:
                        failed += 1
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    return deleted, failed


def purge_local_uploads() -> int:
    """清掉后端主机上残留的本地素材（迁移脚本不删本地文件，这里一并清）。"""
    d = Path(settings.upload_dir)
    if not d.is_dir():
        return 0
    n = 0
    for f in d.iterdir():
        if f.is_file():
            f.unlink()
            n += 1
    return n


async def main(seed: bool, bucket: str | None) -> None:
    print(f"目标库：{engine.url.database} @ {engine.url.host}")
    dropped = await drop_everything()
    print(f"✓ 已删除 {len(dropped)} 张表")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        created = await conn.run_sync(lambda c: inspect(c).get_table_names())
    print(f"✓ 已重建 {len(created)} 张空表")

    async with SessionFactory() as session:
        if seed:
            await seed_all(session)
            print("✓ 已灌入演示数据（商品 / 门店 / 示例页面）")
        await ensure_admin(session)
        await session.commit()
    print(f"✓ 管理员账号已就绪：{settings.admin_username}")
    await engine.dispose()

    if bucket:
        d, f = purge_assets(bucket)
        print(f"✓ 对象存储 {bucket}/uploads/ 已删除 {d} 个对象" + (f"，失败 {f} 个" if f else ""))
        n = purge_local_uploads()
        print(f"✓ 本地 {settings.upload_dir} 清掉 {n} 个残留文件")

    print("\n后续步骤：")
    print("  1. 小程序：清除数据缓存后重进（首页/关于品牌有本地秒开缓存）")
    print("  2. 管理端：登录 → 建品类 → 建系列 → 上传商品")
    print("  3. 「页面管理」配首页与关于品牌；「商城配置」配左菜单图片跳链")
    if not seed:
        print("  注：未灌演示数据，商品/品类/页面现在都是空的，属正常")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="线上环境归零：清库 + 清素材（不可逆）")
    ap.add_argument("--confirm", metavar="库名", help="必须与实际库名一致才执行")
    ap.add_argument("--purge-assets", metavar="桶名",
                    help="同时清空对象存储 uploads/ 下全部素材，需写对桶名")
    ap.add_argument("--seed", action="store_true", help="重建后灌入演示数据")
    args = ap.parse_args()

    db = engine.url.database
    if args.confirm != db:
        sys.exit(f"✗ 未确认，什么都没做。\n"
                 f"  当前连接的库是 `{db}`（{engine.url.host}）。\n"
                 f"  确认要清空请重跑：--confirm {db}")

    if args.purge_assets:
        if not s3_enabled():
            sys.exit("✗ S3_* 未配置，无法清理对象存储。去掉 --purge-assets 可只清库。")
        if args.purge_assets != settings.s3_bucket:
            sys.exit(f"✗ 桶名不匹配，什么都没做。\n"
                     f"  当前配置的桶是 `{settings.s3_bucket}`。\n"
                     f"  确认要清空素材请重跑：--purge-assets {settings.s3_bucket}")

    asyncio.run(main(seed=args.seed, bucket=args.purge_assets))
