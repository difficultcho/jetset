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

# 7. 管理后台静态目录（CI 通过 scp 发布到这里）
mkdir -p /var/www/jetset-admin
chown -R <SSH_USER>: /var/www/jetset-admin
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
