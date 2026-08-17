"""排查「商城选中系列后右侧空白」：把下钻入口的派生链一步步打出来。

在服务器上执行：
    docker compose exec api python -m scripts.check_series_menu

只读：不改库、不写对象存储。

背景：系列的下钻入口不是人工配的，是从商品倒推出来的
（services/shop.py::_series_top_categories）：

    系列 → 它的在售商品 → 商品挂的叶子类目 → 向上归并到一级类目 → 去重

「叶子」= 没有子类目的类目，与层级无关：二级类目归并到 parent_id，
没建二级的一级类目本身就是叶子，归并到它自己。

这条链上任何一环断了，右侧就是空白。断点有四种，本脚本逐一指出是哪种。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db import SessionFactory, engine  # noqa: E402
from app.models.catalog import Category, Spu  # noqa: E402
from app.models.series import Series  # noqa: E402
from app.models.shop import ShopMenu  # noqa: E402


async def main() -> None:
    async with SessionFactory() as s:
        series = (await s.execute(select(Series).order_by(Series.id))).scalars().all()
        cats = {c.id: c for c in (await s.execute(select(Category))).scalars()}
        menus = {m.ref_id: m for m in (await s.execute(select(ShopMenu))).scalars()
                 if m.kind == "series"}
        has_children = {c.parent_id for c in cats.values() if c.parent_id is not None}

        if not series:
            print("库里一个系列都没有。")
            return

        for se in series:
            flag = "" if se.status == 1 else "   ← 系列已停用，菜单项会自动隐藏"
            print(f"\n{'=' * 64}\n系列 #{se.id}「{se.name}」status={se.status}{flag}")

            row = menus.get(se.id)
            if row is None:
                print("  △ 没在「商城配置」里加过 → 左菜单根本不显示它")
            elif row.status != 1:
                print("  △ 商城配置里状态是「隐藏」→ 左菜单不显示它")

            spus = (await s.execute(select(Spu).where(Spu.series_id == se.id))).scalars().all()
            if not spus:
                print("  ✗ 断点1：没有任何商品归属这个系列")
                print("     → 去「商品管理」逐个编辑商品，把「系列」选成它")
                continue

            on_sale = [p for p in spus if p.status == 1]
            print(f"  商品共 {len(spus)} 个，其中在售 {len(on_sale)} 个")
            for p in spus:
                c = cats.get(p.category_id)
                if c is None:
                    cname = f"?? 类目#{p.category_id} 在库里不存在"
                else:
                    lvl = "一级" if c.parent_id is None else "二级"
                    leaf = "叶子" if c.id not in has_children else "有子类目"
                    cname = f"{c.name}(#{c.id}, {lvl}/{leaf})"
                print(f"    - #{p.id}「{p.name}」status={p.status}  类目={cname}")

            if not on_sale:
                print("  ✗ 断点2：商品都下架了（status=0），派生只认在售商品")
                print("     → 商品管理里把它们上架")
                continue

            # 归并：有父级的归到父级，没父级的（叶子一级类目）归到它自己
            rolled, dangling = [], []
            for p in on_sale:
                c = cats.get(p.category_id)
                if c is None:
                    dangling.append(p)
                    continue
                top = cats.get(c.parent_id) if c.parent_id is not None else c
                if top is None:
                    dangling.append(p)
                else:
                    rolled.append((p, c, top))
            if dangling:
                print("  ✗ 断点3：以下在售商品挂的类目在库里查不到（外键悬空）")
                for p in dangling:
                    print(f"     - 商品 #{p.id}「{p.name}」→ 类目#{p.category_id}")
                print("     → 编辑这些商品，重新选一个存在的类目")
            if not rolled:
                continue

            tops, disabled = {}, {}
            for _p, _c, top in rolled:
                (tops if top.status == 1 else disabled)[top.id] = top
            if disabled:
                print("  ✗ 断点4：归并出的一级类目被停用了，入口跟着消失")
                for t in disabled.values():
                    print(f"     - 一级类目「{t.name}」(#{t.id}) status={t.status}")
                print("     → 品类管理里启用它，或把商品换到启用的类目下")

            # 不是故障，但值得提醒：类目既有子类目、又直接挂了商品
            mixed = {c.id: c for _p, c, _t in rolled if c.id in has_children}
            if mixed:
                for c in mixed.values():
                    print(f"  △ 类目「{c.name}」(#{c.id}) 有子类目却直接挂了商品："
                          f"入口能出来，但按它的子类目浏览时会漏掉这些商品")
                print("     → 建议把这些商品改挂到某个子类目下")

            if tops:
                names = "、".join(t.name for t in
                                 sorted(tops.values(), key=lambda x: (x.sort, x.id)))
                print(f"  ✓ 会派生出 {len(tops)} 个下钻入口：{names}")
            else:
                print("  ✗ 最终派生结果为空 → 右侧下部空白")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
