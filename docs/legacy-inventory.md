# 历史遗留盘点清单

三类遗留，互不依赖，可分别执行。命令都在**服务器上**跑（`docker compose exec api` 进 api 容器）。

> 标注说明：🔍 只读 / ⚠️ 会改动 / 💾 执行前先备份

---

## A. 素材迁移：后端主机 → 对象存储

**背景**：接对象存储之前上传的素材落在 api 容器的 `uploads/` 目录里。容器重建会丢，也没 CDN。

**关键前提**：库里存的一直是 `/uploads/<文件名>` 这种相对路径，前端用 `ASSET_BASE` 拼域名——**迁移只搬文件，不改数据库**。

### A1 🔍 确认对象存储已配齐

```bash
docker compose exec api python -c "from app.api.uploads import s3_enabled; \
print('✓ S3 已启用' if s3_enabled() else '✗ 未配置，仍在写本地磁盘')"
```

输出 ✗ 说明 `S3_ENDPOINT/S3_BUCKET/S3_ACCESS_KEY/S3_SECRET_KEY` 没配全，先补 `.env` 再往下走。

### A2 🔍 看存量有多少

```bash
docker compose exec api python -c "
from app.config import settings
from pathlib import Path
p = Path(settings.upload_dir)
fs = [f for f in p.iterdir() if f.is_file()] if p.is_dir() else []
print(f'{p.resolve()} → {len(fs)} 个文件，{sum(f.stat().st_size for f in fs) // 1024 // 1024} MB')
"
```

`0 个文件` = 没有存量，A 段跳过。

### A3 ⚠️ 执行迁移（幂等，可反复跑）

```bash
docker compose exec api python scripts/migrate_uploads_s3.py
```

同名同大小的对象会跳过，**不删本地文件**。

> **如果报 `ModuleNotFoundError: No module named 'app'`**
>
> 说明容器里是修复前的旧脚本。`python scripts/x.py` 只把 `scripts/` 放进 `sys.path`，
> 项目根 `/code` 不在里面。两个办法：
>
> ```bash
> # 立刻可用，不必重新部署：-m 会把工作目录（/code）加进 sys.path
> docker compose exec api python -m scripts.migrate_uploads_s3
> ```
>
> 或者重新部署一次，脚本已加了 `sys.path` 引导，两种跑法都能用。

### A4 🔍 抽查

```bash
curl -I https://<素材域名>/uploads/<A3 输出里的任一文件名>
```

期望 `200` 且带 `Cache-Control`。再到小程序里翻几个老商品/老页面，图能出来即可。

### A5 ⚠️ 清本地（可选，建议观察一两周再做）

确认线上素材都从对象存储走之后，再删容器里的本地文件。不急——留着不影响任何东西。

---

## B. 孤儿表：库里有、代码里没有

**背景**：`banner` 表的模型和接口在「清理悬空链路」时已删除，表和数据还在。可能还有别的。

### B1 🔍 列出所有孤儿表

```bash
docker compose exec api python -c "
import asyncio
from sqlalchemy import inspect
from app.db import engine, Base
from app import models  # noqa: F401  确保模型注册

async def main():
    async with engine.begin() as c:
        db = set(await c.run_sync(lambda x: inspect(x).get_table_names()))
    code = set(Base.metadata.tables)
    print('孤儿表（库里有、代码没有）:', sorted(db - code) or '无')
    print('未建表（代码有、库里没有）:', sorted(code - db) or '无')
    await engine.dispose()

asyncio.run(main())
"
```

- **孤儿表** → 走 B2
- **未建表** → 不正常，说明模型没注册或启动没跑 `create_all`，先查这个

### B2 🔍 看孤儿表里有多少数据

```sql
SELECT COUNT(*) FROM banner;   -- 对 B1 列出的每张表都查一遍
```

### B3 💾⚠️ 备份后删除

```bash
# 先备份（只备这几张表）
docker compose exec db mysqldump -u<用户> -p jetset banner > banner_backup_$(date +%F).sql

# 确认备份文件不为空后再删
```

```sql
DROP TABLE banner;
```

**不着急删**。孤儿表不影响运行，只占空间。真正的收益是让 `SHOW TABLES` 干净、以后不会有人误用。

---

## C. 脏配置数据：模型变更留下的旧值

### C1 🔍 找出还带旧版跳转的页面

配置模型重构时 `post` / `campaign` 两种链接类型被合并成了 `page`，旧页面里可能还存着。

```sql
SELECT `key`, title FROM page
WHERE JSON_SEARCH(blocks, 'one', 'post')     IS NOT NULL
   OR JSON_SEARCH(blocks, 'one', 'campaign') IS NOT NULL;
```

### C2 ⚠️ 处理方式：管理端点一遍，别手改 SQL

管理端已经有自愈逻辑：打开这些页面时会弹

> 「N 处旧版跳转配置已失效，已重置为「不跳转」，请重新选择目标后保存」

**照着 C1 的结果逐个打开 → 重新选跳转目标 → 保存**，脏数据就洗掉了。手写 SQL 改 JSON 又慢又容易错，不划算。

同理，「商城配置」页里的图片跳链也有同样的自愈（打开即降级），有配过就顺手看一眼。

### C3 🔍 指向已删对象的跳转 —— 不用查

页面/商品/类目被删后，C 端解析时链接自动降级为 `null`，块变成不可点，不报错也不崩。这是设计好的行为，不是故障。真要清理，看到哪个不可点就去管理端重配即可。

---

## 执行顺序建议

1. **A 段优先** —— 素材还在容器里是真实风险（容器重建即丢）
2. **C 段次之** —— 影响运营体验，但有自愈兜底，不紧急
3. **B 段最后** —— 纯洁癖，零风险零收益，有空再说

## 已知不做

- 颜色筛选需要新增 `color_family` 字段（当前颜色名品牌化命名不可归并）
- `Sku.size` 是自由文本，没有枚举约束，脏值会直接变成筛选项
