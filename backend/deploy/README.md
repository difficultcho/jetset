# 部署指南（CI/CD + 云服务器）

流水线：`git push main` → GitHub Actions 跑测试 → 构建镜像推 TCR → SSH 到服务器拉取重启。
工作流定义见 [.github/workflows/backend.yml](../../.github/workflows/backend.yml)。

## 一、服务器首次准备（只做一次）

```bash
# 1. 安装 docker（已装可跳过）
curl -fsSL https://get.docker.com | sh

# 2. 部署目录
mkdir -p /opt/jetset && cd /opt/jetset

# 3. 放置编排文件：把仓库里 backend/deploy/docker-compose.server.yml 上传为
#    /opt/jetset/docker-compose.yml

# 4. 写 .env（参考 backend/.env.example，重点改这些）：
#    APP_ENV=prod
#    ROOT_PATH=/jetset         # nginx 路径前缀反代（/jetset/ → 127.0.0.1:8010）
#    DATABASE_URL=mysql+aiomysql://jetset:密码@<你的MySQL>:3306/jetset?charset=utf8mb4
#    REDIS_URL=redis://redis:6379/0
#    JWT_SECRET=<openssl rand -hex 32>
#    WECHAT_MOCK=true          # 上线前改 false 并配 WECHAT_APPID/SECRET
#    PAYMENT_PROVIDER=mock     # 商户号下来后改 wechat

# 5. 登录 TCR 并首次启动
docker login ccr.ccs.tencentyun.com
docker compose up -d                       # 服务器已有 MySQL
# docker compose --profile withdb up -d    # 或使用内置 MySQL
docker compose exec api python -m app.seed

# 6. nginx：在现有 bce.kkmsee.com server 块中加 /jetset/ 前缀反代
#    （见 nginx.conf.example 方案 A），reload 后验证：
#    curl https://bce.kkmsee.com/jetset/healthz

# 7. 管理后台静态目录（CI 通过 scp 发布到这里；必须由部署用户拥有，
#    CI 每次发布会清空其内容后重新上传）
sudo mkdir -p /var/www/jetset-admin
sudo chown -R <SSH_USER对应的用户>: /var/www/jetset-admin
#    nginx 加 /jetset-admin/ 静态块（见 nginx.conf.example）
#    访问 https://bce.kkmsee.com/jetset-admin/
#    初始账号 = .env 的 ADMIN_USERNAME/ADMIN_PASSWORD（seed 创建），登录后右上角改密码
```

## 二、GitHub 仓库配置（只做一次）

1. 在 TCR 控制台创建镜像仓库 `mz_personal_namespace/jetset-api`（命名空间按实际改，
   同时改 workflow 里的 `IMAGE` 和 docker-compose.server.yml 里的 image）
2. 生成部署密钥：`ssh-keygen -t ed25519 -f jetset_deploy`，公钥追加到服务器
   `~/.ssh/authorized_keys`
3. 仓库 Settings → Secrets → Actions 添加：

| Secret | 值 |
|---|---|
| `TCR_USERNAME` | 腾讯云容器镜像服务用户名 |
| `TCR_PASSWORD` | TCR 密码 |
| `SSH_HOST` | 服务器公网 IP |
| `SSH_USER` | SSH 用户（root/ubuntu） |
| `SSH_KEY` | jetset_deploy 私钥全文 |

## 三、小程序侧

1. `miniprogram/utils/config.js` 的 `API_BASE` 改为 `https://bce.kkmsee.com/jetset`
2. 小程序后台（mp.weixin.qq.com）→ 开发管理 → 开发设置 → 服务器域名 →
   request 合法域名 / uploadFile 合法域名 添加 `https://bce.kkmsee.com`
   （域名级配置，路径前缀不影响）
3. 真机测试：开发者工具「预览」扫码即可；未配域名前手机需打开
   胶囊菜单 → 开发调试 后重进小程序

## 四、日常发布

```bash
git push origin main     # 其余全自动：测试 → 构建 → 推送 → 部署
```

回滚：服务器上 `docker compose pull api worker` 前镜像都带 commit SHA tag，
`docker compose up -d` 前把 compose 里 image 改为指定 SHA 即可。

## 对象存储 + CDN 素材迁移（S3 兼容协议，配置指向百度 BOS；四步，任意中间状态不断图）

前置（百度云控制台）：
- BOS bucket 设「公共读、私有写」，记下 bucket 名与地域（如 bj）
- CDN 添加加速域名（如 cdn.kkmsee.com，HTTPS 证书，源站选该 BOS bucket）
- 建子用户 AK/SK，只授予该 bucket 读写（不要用主账号密钥）
- 注意：BOS 直连域名 `*.bcebos.com` 不是 CDN，加速域名才是

### 1. 服务器开启对象存储上传（.env 追加，然后 docker compose up -d）
```
S3_ENDPOINT=https://s3.bj.bcebos.com   # BOS 的 S3 兼容端点，地域对应改
S3_REGION=bj
S3_ACCESS_KEY=xxx
S3_SECRET_KEY=xxx
S3_BUCKET=xxx
ASSET_BASE_URL=https://cdn.kkmsee.com  # 素材公网域名（CDN 加速域名）
```
生效后：新上传直接进对象存储（键 uploads/<uuid>，带一年 immutable 缓存头）；
API 伺服 /uploads/x 时本地有文件走本地，没有则 302 到 ASSET_BASE_URL —— 老图不受影响。
（协议是 S3 兼容的，将来换腾讯 COS/阿里 OSS 只改这几个环境变量。）

### 2. 存量素材迁移（服务器上执行一次，幂等可重跑）
```
cd /opt/jetset && docker compose exec api python scripts/migrate_uploads_s3.py
```
迁完抽查：curl -I https://cdn.kkmsee.com/uploads/<任意老文件名> 应为 200。
本地卷文件可以保留（双保险），想回收磁盘再清。

### 3. 前端切 CDN 直连（省掉 302 一跳）
- miniprogram/utils/config.js 的 `CDN` 常量填素材域名，小程序重新发版
- admin/src/api.js 的 `CDN_BASE` 填素材域名，push 触发 CI 重新部署
- 小程序后台「downloadFile 合法域名」加素材域名

### 4. 收尾
- backup.sh 里的 uploads 打包段可以注释掉（素材正本已在对象存储）
- CDN 控制台建议开：Range 回源（视频拖动进度条）、HTTP 强跳 HTTPS
