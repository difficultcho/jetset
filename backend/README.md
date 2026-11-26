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
| `MOCK_MODE` | true：假登录、假支付、跳过内容安全。false 才走真实登录和微信支付 |
| `WECHAT_APPID` / `WECHAT_SECRET` | 关闭 mock 后必填（code2session）。必须是实际上线的小程序 AppID |
| `WECHAT_MSG_TOKEN` | 小程序消息推送 Token。明文 JSON。不配则不接收。URL 见 `.env.example` |
| `WXPAY_*` | 关闭 mock 后必填。JSAPI 下单和回调验签已实现，见 `.env.example` |
| `ORDER_TIMEOUT_MINUTES` | 待付款超时时长，超时由 arq 任务/定时扫描自动取消并回补库存 |
| `AUTO_CREATE_TABLES` | MVP 启动建表；schema 稳定后改 alembic 并关闭 |

## 约定

- **金额一律为整数「分」**（如 ¥2399 → 239900），前端展示时 `/100`
- 统一响应包裹 `{ code, message, data }`，`code=0` 成功
- 订单状态: `pending_payment / pending_shipment / pending_receipt / pending_review / completed / cancelled / refund_pending / refunded`，响应含中文 `status_label`
- 退款由管理端在客服核验后整单原路发起。小程序没有自主退货。未发货的已支付订单、待收货、已完成都可以退，代码不锁 7 天；帮助文案写快递送达后 7 天、买家自费退回、查验后再退。经营税由会计处理
- 正式环境的确认收货打开微信组件。服务器用 get_order 核对状态为确认收货或交易完成后，才把订单改为已完成。用户在微信里确认，或快递第 10 天自动确认，靠消息推送 `trade_manage_order_settlement` 收口。mock 仍直接确认。管理端「完成」只改本系统状态
- 商品按 SPU/SKU 建模，加购/下单传 `sku_id`；下单用条件更新扣库存防超卖，取消、超时、退款成功都会回补

## 迁移（schema 稳定后）

```bash
.venv/bin/alembic revision --autogenerate -m "init"
.venv/bin/alembic upgrade head
# 然后设置 AUTO_CREATE_TABLES=false
```

## 待办（二期起）

- 订阅消息。发货信息录入已接在管理端发货上：非 mock 先请求微信，失败则订单保持待发货。录入成功后微信才开始结算；退款成功要在发货管理里显示已退款，也要先有这次录入
- 管理端 API（`/api/admin/*`，RBAC）：商品/订单/售后/批发审核/运营位
- 优惠券/积分：金额试算已在 `orders.preview` 收口，扩展 `discount_amount` 即可
- 上传从本地磁盘切换 COS 直传签名
