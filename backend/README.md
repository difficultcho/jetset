# JETSET Shop 后端（FastAPI）

技术栈：FastAPI + SQLAlchemy 2 (async) + MySQL 8 + Redis + arq。
设计文档见 [../docs/backend-design.md](../docs/backend-design.md)。

## 本地开发（venv + sqlite，最快路径）

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 默认配置即 sqlite + mock 微信/支付，无需任何外部服务
.venv/bin/python -m app.seed                      # 建表 + 灌入设计稿商品数据
.venv/bin/uvicorn app.main:app --reload           # http://127.0.0.1:8000/docs

.venv/bin/pytest                                  # 运行测试
```

## Docker（MySQL + Redis 全套）

```bash
cd backend
cp .env.example .env                              # 按需修改
docker compose up -d --build
docker compose exec api python -m app.seed        # 灌种子数据
# API:  http://127.0.0.1:8000/docs
# 生产: docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 配置要点（.env）

| 变量 | 说明 |
|---|---|
| `WECHAT_MOCK` | true 时 `POST /auth/login` 的 code 直接映射 openid，不请求微信 |
| `WECHAT_APPID` / `WECHAT_SECRET` | 关闭 mock 后必填（code2session） |
| `PAYMENT_PROVIDER` | `mock`：`POST /payments/mock/confirm` 模拟支付成功；`wechat`：待商户号配置后实现 |
| `ORDER_TIMEOUT_MINUTES` | 待付款超时时长，超时由 arq 任务/定时扫描自动取消并回补库存 |
| `AUTO_CREATE_TABLES` | MVP 启动建表；schema 稳定后改 alembic 并关闭 |

## 约定

- **金额一律为整数「分」**（如 ¥2399 → 239900），前端展示时 `/100`
- 统一响应包裹 `{ code, message, data }`，`code=0` 成功
- 订单状态: `pending_payment / pending_shipment / pending_receipt / pending_review / completed / cancelled`，响应含中文 `status_label`
- 商品按 SPU/SKU 建模，加购/下单传 `sku_id`；下单用条件更新扣库存防超卖，取消/超时回补

## 迁移（schema 稳定后）

```bash
.venv/bin/alembic revision --autogenerate -m "init"
.venv/bin/alembic upgrade head
# 然后设置 AUTO_CREATE_TABLES=false
```

## 待办（二期起）

- 微信支付 JSAPI 真实接入（`app/services/payment.py` 的 `WechatPayProvider`）
- 微信发货信息录入 API、订阅消息
- 管理端 API（`/api/admin/*`，RBAC）：商品/订单/售后/批发审核/运营位
- 优惠券/积分：金额试算已在 `orders.preview` 收口，扩展 `discount_amount` 即可
- 上传从本地磁盘切换 COS 直传签名
