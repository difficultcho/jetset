#!/usr/bin/env bash
# JET SET 每日备份：MySQL 全量 dump + uploads 素材卷打包，本地保留 N 天。
#
# 部署（服务器上）：
#   cp backup.sh /opt/jetset/backup.sh && chmod +x /opt/jetset/backup.sh
#   手动跑一次验证：/opt/jetset/backup.sh
#   crontab -e 加一行（每天 03:00）：
#     0 3 * * * /opt/jetset/backup.sh >> /opt/jetset/backup.log 2>&1
#
# 恢复：
#   gunzip < jetset-YYYYmmdd.sql.gz | docker exec -i golf-mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" jetset'
#   （生产恢复以备份为准，不要用 app.seed —— seed 是演示数据）
#
# 接入 COS 后：装好 coscmd 并 coscmd config，本脚本会自动把备份传到 COS 的 backups/ 下；
# 素材迁 COS 后可注释掉 uploads 打包段。
set -euo pipefail

MYSQL_CONTAINER="golf-mysql"        # 现有 MySQL 容器名
DB_NAME="jetset"
UPLOAD_VOLUME="jetset_upload_data"  # docker volume ls 可确认
BACKUP_DIR="/opt/jetset/backups"
KEEP_DAYS=14
# 打包 uploads 用的镜像：服务器连不上 Docker Hub，复用已有的 api 镜像（自带 tar）
TAR_IMAGE="ccr.ccs.tencentyun.com/mz_personal_namespace/jetset-api:latest"

DATE=$(date +%Y%m%d-%H%M)
mkdir -p "$BACKUP_DIR"

# 1) MySQL：--single-transaction 不锁表；密码取容器内环境变量（单引号故意不在宿主机展开）
docker exec "$MYSQL_CONTAINER" sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines '"$DB_NAME"'' \
  | gzip > "$BACKUP_DIR/jetset-$DATE.sql.gz"
echo "✓ MySQL -> jetset-$DATE.sql.gz ($(du -h "$BACKUP_DIR/jetset-$DATE.sql.gz" | cut -f1))"

# 2) uploads 素材卷（迁 COS 后可注释本段）
docker run --rm --entrypoint tar \
  -v "$UPLOAD_VOLUME":/data:ro -v "$BACKUP_DIR":/backup \
  "$TAR_IMAGE" czf "/backup/uploads-$DATE.tgz" -C /data .
echo "✓ uploads -> uploads-$DATE.tgz ($(du -h "$BACKUP_DIR/uploads-$DATE.tgz" | cut -f1))"

# 3) 本地保留 KEEP_DAYS 天
find "$BACKUP_DIR" -name '*.gz' -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR" -name '*.tgz' -mtime +"$KEEP_DAYS" -delete

# 4) 已配置 coscmd 则异地上传（灾备真正生效的一步）
if command -v coscmd >/dev/null 2>&1; then
  coscmd upload "$BACKUP_DIR/jetset-$DATE.sql.gz" "backups/jetset-$DATE.sql.gz" \
    && coscmd upload "$BACKUP_DIR/uploads-$DATE.tgz" "backups/uploads-$DATE.tgz" \
    && echo "✓ 已上传 COS backups/"
fi

echo "备份完成：$DATE"
