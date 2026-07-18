"""存量素材迁移：把本地 uploads/ 目录全量上传到 S3 兼容对象存储（百度 BOS 等）。

在服务器上执行（api 容器内自带 boto3 和 S3_* 环境变量）：
    docker compose exec api python scripts/migrate_uploads_s3.py

幂等：对象已存在（同大小）则跳过，可反复执行；不删除本地文件。
"""
import mimetypes
import sys
from pathlib import Path

from app.api.uploads import CACHE_CONTROL, s3_client, s3_enabled
from app.config import settings


def main() -> None:
    if not s3_enabled():
        sys.exit("✗ S3_* 环境变量未配齐（endpoint/bucket/access_key/secret_key）")
    src = Path(settings.upload_dir)
    files = sorted(p for p in src.iterdir() if p.is_file()) if src.is_dir() else []
    if not files:
        sys.exit(f"目录为空：{src}")

    client = s3_client()
    done = skipped = 0
    for f in files:
        key = f"uploads/{f.name}"
        try:
            head = client.head_object(Bucket=settings.s3_bucket, Key=key)
            if head["ContentLength"] == f.stat().st_size:
                skipped += 1
                continue
        except Exception:
            pass  # 不存在 → 上传
        mime = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        client.put_object(Bucket=settings.s3_bucket, Key=key, Body=f.read_bytes(),
                          ContentType=mime, CacheControl=CACHE_CONTROL)
        done += 1
        print(f"✓ {key} ({f.stat().st_size // 1024}KB {mime})")

    print(f"\n完成：上传 {done}，跳过（已存在）{skipped}，共 {len(files)}")
    print("抽查：curl -I <素材域名>/uploads/<任一文件名> 应为 200 且带 Cache-Control")


if __name__ == "__main__":
    main()
