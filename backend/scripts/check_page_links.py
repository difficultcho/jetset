"""脏跳转排查：找出页面块 / 商城图片跳链里不符合当前链接规则的配置，精确定位到块。

配置模型重构时 post / campaign 两种链接类型合并成了 page，旧数据可能还存着。
管理端打开时会自动降级为「不跳转」并提示，但得先知道该去开哪个页面。

在服务器上执行：
    docker compose exec api python -m scripts.check_page_links

只读：不改库。输出即「该去管理端打开哪几个页面、看第几块」。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import SessionFactory, engine  # noqa: E402
from app.models.catalog import Category, Spu  # noqa: E402
from app.models.cms import Page  # noqa: E402
from app.models.series import Series  # noqa: E402
from app.models.shop import ShopMenu  # noqa: E402
from app.services.pages import LINK_KINDS  # noqa: E402


def _bad_kind(link) -> str | None:
    """返回不合法的 kind（None 表示这个链接没问题）。"""
    if link is None:
        return None
    if not isinstance(link, dict):
        return "（不是对象）"
    kind = link.get("kind")
    return None if kind in LINK_KINDS else f"kind={kind!r}"


def _scan_block(b: dict, i: int) -> list[str]:
    """一个块里可能挂 1~2 个链接（链接行左右各一个）。"""
    out = []
    if not isinstance(b, dict):
        return [f"第 {i} 块：不是对象"]
    if b.get("kind") == "linkrow":
        for side, label in (("left", "左"), ("right", "右")):
            s = b.get(side) or {}
            bad = _bad_kind(s.get("link")) if isinstance(s, dict) else "（不是对象）"
            if bad:
                out.append(f"第 {i} 块（链接行·{label}）{bad}")
    else:
        bad = _bad_kind(b.get("link"))
        if bad:
            out.append(f"第 {i} 块（{b.get('kind')}）{bad}")
    return out


async def main() -> None:
    problems = 0
    async with SessionFactory() as s:
        print("=== 页面块 ===")
        pages = (await s.execute(select(Page).order_by(Page.sort, Page.key))).scalars().all()
        for p in pages:
            issues = []
            for i, b in enumerate(p.blocks or [], 1):
                issues += _scan_block(b, i)
            if issues:
                problems += len(issues)
                print(f"\n  页面「{p.title or p.key}」（key={p.key}）")
                for x in issues:
                    print(f"    ✗ {x}")
        if not problems:
            print("  ✓ 没有脏跳转")

        print("\n=== 商城图片跳链 ===")
        shop_bad = 0
        menus = (await s.execute(select(ShopMenu))).scalars().all()
        names = {
            ("series", x.id): x.name
            for x in (await s.execute(select(Series))).scalars()
        } | {
            ("category", x.id): x.name
            for x in (await s.execute(select(Category))).scalars()
        }
        for m in menus:
            issues = []
            for i, b in enumerate(m.banners or [], 1):
                bad = _bad_kind(b.get("link")) if isinstance(b, dict) else "（不是对象）"
                if bad:
                    issues.append(f"第 {i} 张图 {bad}")
            if issues:
                shop_bad += len(issues)
                label = m.title or names.get((m.kind, m.ref_id), f"{m.kind}#{m.ref_id}")
                print(f"\n  菜单项「{label}」")
                for x in issues:
                    print(f"    ✗ {x}")
        if not shop_bad:
            print("  ✓ 没有脏跳转")
        problems += shop_bad

        # 顺带：指向已删对象的跳转（C 端会自动降级为不可点，不是故障，仅供参考）
        print("\n=== 指向已删对象的跳转（仅提示，C 端已自动降级为不可点）===")
        page_keys = {p.key for p in pages}
        spu_ids = set((await s.execute(select(Spu.id))).scalars())
        cat_ids = set((await s.execute(select(Category.id))).scalars())
        series_ids = set((await s.execute(select(Series.id))).scalars())
        dangling = 0

        def check_dangling(link, where: str) -> None:
            nonlocal dangling
            if not isinstance(link, dict):
                return
            k = link.get("kind")
            miss = None
            if k == "page" and link.get("key") not in page_keys:
                miss = f"页面 key={link.get('key')!r} 不存在"
            elif k == "pdp" and link.get("spu_id") not in spu_ids:
                miss = f"商品 id={link.get('spu_id')} 不存在"
            elif k == "list":
                if link.get("category_id") and link["category_id"] not in cat_ids:
                    miss = f"品类 id={link['category_id']} 不存在"
                elif link.get("series_id") and link["series_id"] not in series_ids:
                    miss = f"系列 id={link['series_id']} 不存在"
            if miss:
                dangling += 1
                print(f"    △ {where}：{miss}")

        for p in pages:
            for i, b in enumerate(p.blocks or [], 1):
                if not isinstance(b, dict):
                    continue
                if b.get("kind") == "linkrow":
                    for side in ("left", "right"):
                        sd = b.get(side) or {}
                        if isinstance(sd, dict):
                            check_dangling(sd.get("link"), f"页面「{p.title or p.key}」第 {i} 块·{side}")
                else:
                    check_dangling(b.get("link"), f"页面「{p.title or p.key}」第 {i} 块")
        for m in menus:
            for i, b in enumerate(m.banners or [], 1):
                if isinstance(b, dict):
                    check_dangling(b.get("link"), f"商城菜单 {m.kind}#{m.ref_id} 第 {i} 张图")
        if not dangling:
            print("    ✓ 无")

    print(f"\n{'=' * 40}")
    if problems:
        print(f"需处理：{problems} 处脏跳转。")
        print("处理方式：到管理端打开上面列出的页面 / 菜单项，重新选跳转目标后保存即可")
        print("（打开时会弹提示并自动降级，不用手改 SQL）")
    else:
        print("✓ 全部跳转配置都符合当前规则")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
