# JETSET 购物小程序 — 后端设计与管理/营销功能评估

> 配套前端：`miniprogram/`（原生微信小程序，当前为纯前端 mock）
> 本文档覆盖：后端架构与技术选型、领域模型、API 设计、微信生态对接、
> 以及设计稿中**看不到但运营必需**的管理功能与营销功能评估和分期建议。

---

## 1. 总体架构

```
┌─────────────┐      ┌──────────────┐
│ 微信小程序   │      │ 管理后台 SPA  │  (Vue/React + 管理端组件库)
│ (C端)       │      │ (B端运营)     │
└──────┬──────┘      └──────┬───────┘
       │  HTTPS / JSON      │
       ▼                    ▼
┌────────────────────────────────────┐
│        API 服务（模块化单体）        │
│  auth / catalog / cart / order /   │
│  payment / marketing / wholesale / │
│  cms / admin(RBAC)                 │
└──┬──────────┬──────────┬───────────┘
   ▼          ▼          ▼
 MySQL      Redis     对象存储 COS/OSS
 (主数据)   (缓存/     (商品图/执照/
            延迟队列)   头像, 走 CDN)
       ▲
       │ 回调
┌──────┴───────┐
│ 微信侧：登录、 │
│ 支付、订阅消息、│
│ 发货录入、安审 │
└──────────────┘
```

### 1.1 技术选型（定稿：Python FastAPI）

| 项 | 选型 | 说明 |
|---|---|---|
| API 框架 | **FastAPI**（Python 3.12） | async IO 足够电商 API 体量；Pydantic v2 请求校验 + 自动 OpenAPI 文档，小程序/管理后台联调直接看 `/docs` |
| ORM / 迁移 | SQLAlchemy 2 (async) + Alembic | 订单/库存强事务；迁移版本化，随部署自动执行 |
| 数据库 | MySQL 8 | 与现有运维经验一致 |
| 缓存/队列 | Redis + arq | 商品缓存、库存预占；arq 跑延迟任务（订单超时取消）与定时任务（对账） |
| 微信支付 | `wechatpayv3`（社区库） | 官方无 Python SDK；v3 验签/平台证书轮换需专门测试覆盖 |
| 管理后台 | Vue3 + Element Plus SPA | 静态文件由 nginx 托管，调 `/api/admin/*` |
| 部署 | Docker Compose（api / worker / mysql / redis / nginx） | 测试/生产同构，见 1.2 |

选型依据：本项目为单人开发（AI 辅助）+ 所有者运维，运维方已有 Python + MySQL +
Docker Compose 实践；FastAPI 在同等功能下样板代码最少、迭代最快；性能在此
体量下不构成选型差异。唯一代价是微信支付走社区 SDK，签名/证书逻辑补测试即可。

### 1.2 部署与环境（Docker）

- **镜像**：api（uvicorn）与 worker（arq）共用一个镜像、不同启动入口。
- **环境**：`docker-compose.yml`（基础）+ `docker-compose.prod.yml`（覆盖）。
  - dev：本地 `compose up`，MySQL/Redis 容器化，代码热重载；
  - test/staging：服务器上同一套 compose，独立项目名 + 独立数据库 + 独立 `.env`；
  - prod：nginx（TLS 终止 + 托管管理后台静态文件）→ api ×N 副本。
- **配置**：全部走环境变量（pydantic-settings），`.env` 按环境分文件、不进 git。
- **发布**：git push → CI 构建镜像推仓库 → 服务器拉取 → `alembic upgrade head` → 重启。
- **合规前置**：微信小程序 request 合法域名要求 **HTTPS + ICP 备案域名**；
  TLS 用 caddy 自动证书或 nginx + certbot。
- **数据安全**：mysqldump 每日备份至 COS；错误监控接 Sentry（免费档够用）。
- **扩展路径**：API 无状态 → nginx upstream 加副本；MySQL/Redis 到瓶颈迁云托管
  （TencentDB/云 Redis）；worker 按队列长度独立扩容。走到需要 k8s 之前余量很长。

**关于微信云开发（云函数 + 云数据库）**：如果只想快速跑通 MVP、没有独立运维，
可以用云开发替代自建后端，开发成本最低。但有管理后台、优惠券/会员营销、
未来批发（B2B）体系的诉求时，文档型云数据库和云函数会越来越吃力。
**建议：直接自建 API 服务**，一步到位，管理后台与小程序共用同一套 API。

---

## 2. 领域模型（核心表设计）

### 2.1 用户与认证

```
user            id, openid, unionid, phone, name, avatar, gender,
                birthday, region, member_level_id, points, balance,
                reco_enabled(个性化推荐开关), status, created_at
```

- 登录：`wx.login` → 后端 `code2session` → 建/查 user → 签发 JWT。
- 手机号：`getPhoneNumber` 开放能力换取，替换 mock 的 `155****7281`。
- 头像/昵称：`chooseAvatar` + 昵称填写，入库前过内容安全检测。

### 2.2 商品（SPU/SKU）

设计稿里价格挂在商品上、颜色×尺码只是属性；真实系统必须落到 SKU：

```
category        id, parent_id, name, sort, status          （阿尔卑斯系列 → 冲锋衣…）
spu             id, category_id, name, en_model, brief, detail_html,
                badge(热销), status(上架/下架), sort, created_at
spu_image       id, spu_id, color_key, url, sort           （替换前端 CSS 占位图）
sku             id, spu_id, color_name, color_hex, size, price,
                stock, sku_code, status
```

- 前端 `utils/data.js` 的 `PRODS` 结构 ≈ SPU + 颜色/尺码枚举，迁移时
  由「颜色×尺码」笛卡尔积生成 SKU，价格/库存按 SKU 维护。
- 商品列表/详情接口做 Redis 缓存，后台改动时失效。

### 2.3 购物车

```
cart_item       id, user_id, sku_id, qty, created_at    UNIQUE(user_id, sku_id)
```

服务端购物车（当前前端本地 Storage 仅作离线兜底），登录后合并。

### 2.4 订单与支付

```
order           id, order_no, user_id, status, item_amount, discount_amount,
                freight, pay_amount, coupon_user_id, note,
                addr_snapshot(JSON), paid_at, shipped_at, completed_at,
                cancelled_at, created_at
order_item      id, order_id, sku_id, spu_name, en_model, color, size,
                image, price(成交价快照), qty
payment         id, order_id, wx_transaction_id, amount, status, paid_at
shipment        id, order_id, company, tracking_no, shipped_at
after_sale      id, order_id, order_item_id, type(退款/退货/换货),
                reason, images, amount, status(待审核/同意/拒绝/完成), created_at
```

**订单状态机**（对齐前端 5 个筛选 Tab）：

```
待付款 ──支付回调──▶ 待发货 ──录入运单──▶ 待收货 ──确认/超时──▶ 待评价 ──▶ 已完成
   │                                                    
   └─ 超时30min未付/用户取消 ──▶ 已取消（延迟队列驱动，释放库存）
任一已付款状态 ──售后──▶ 退款/售后子流程
```

关键点：
- **库存**：下单预占（Redis 原子扣减 + DB 乐观锁），支付成功落库，取消回补。
- **支付**：微信支付 JSAPI。`POST /orders/:id/pay` 返回 prepay 参数，
  回调 `POST /payment/wechat/notify` 必须幂等（按 transaction_id 去重）。
- **发货**：除物流单号外，需调微信**发货信息录入接口**（平台合规要求）。
- 前端当前「提交订单→直接待付款」，接入后中间插入拉起支付一步。

### 2.5 地址

```
address         id, user_id, name, phone, province, city, district,
                detail, is_default, created_at
```

建议前端后续把「省市区+详细地址」单输入框升级为 `picker mode="region"` + 详细地址。

### 2.6 批发合作（B 端线索）

```
wholesale_application   id, user_id, type(经销商/分销商/门店/其他), phone,
                        company, region, license_img, store_img,
                        status(待审核/通过/驳回), review_note, reviewed_by, created_at
```

- 前端当前提交即成功且无校验 → 接入后做必填校验 + 图片先传 COS 再提交。
- 审核结果通过**订阅消息**通知申请人（对应设计稿"1-3 个工作日内联系"）。
- 中长期：若批发业务做重，演进为经销商账号体系 + 阶梯价/专属价 + 批量下单（B2B 模块），本期不做。

### 2.7 内容/运营位（CMS）

设计稿首页的轮播文案、精选好物、热销排序目前全部写死在前端，必须后台可配：

```
banner          id, position(home_hero), title, sub_title, image, link, sort, status, start/end_at
home_section    id, type(hot_list/featured/grid), spu_ids(JSON), sort, status
```

### 2.8 管理端账号

```
admin_user      id, username, password_hash, role_id, status, last_login_at
role / permission / role_permission        （RBAC）
audit_log       id, admin_id, action, target, detail(JSON), created_at
```

---

## 3. C 端 API 设计（与现有页面一一对应）

统一前缀 `/api/v1`，JWT 鉴权，响应 `{ code, message, data }`。

| 页面 | 接口 |
|---|---|
| 登录 | `POST /auth/login` (code)、`POST /auth/phone` |
| 首页 | `GET /home`（聚合：banner + 热销 + 精选 + 网格，一次请求） |
| 商城 | `GET /categories`；`GET /products?cat=&q=&sort=&page=`（排序 Tab 综合/销量/价格/上新在此实现） |
| 商详 | `GET /products/:id`（含 SKU 列表、每色图片组） |
| 加购弹窗 | `POST /cart/items` (sku_id, qty) |
| 购物车 | `GET /cart`、`PATCH /cart/items/:id`、`DELETE /cart/items/:id` |
| 确认订单 | `POST /orders/preview`（items → 金额试算/可用券/运费）、`POST /orders`（幂等键防重复提交） |
| 支付 | `POST /orders/:id/pay`、回调 `POST /payment/wechat/notify` |
| 订单列表/详情 | `GET /orders?status=&q=`、`GET /orders/:id`、`POST /orders/:id/cancel`、`POST /orders/:id/confirm` |
| 售后 | `POST /orders/:id/after-sales`、`GET /after-sales/mine` |
| 地址 | `GET/POST /addresses`、`PUT/DELETE /addresses/:id`、`PUT /addresses/:id/default` |
| 个人信息 | `GET /me`、`PUT /me`（昵称/头像过内容安全） |
| 批发 | `POST /wholesale/applications`、`GET /wholesale/applications/mine` |
| 上传 | `POST /uploads/credential`（COS 直传签名，后端不代理文件流） |
| 营销 | `GET /coupons/center`、`POST /coupons/:id/claim`、`GET /me/coupons`、`GET /me/points/logs` |

管理端 API 挂 `/api/admin/*`，独立鉴权（账号密码 + RBAC），资源与上表同构（商品、订单、售后、批发审核、CMS、优惠券、用户、看板）。

---

## 4. 管理功能评估（设计稿看不到，但没有就无法运营）

设计稿只交付了 C 端。以下按优先级评估：

### P0 — 上线前必须

| 模块 | 说明 | 备注 |
|---|---|---|
| 商品管理 | SPU/SKU 增删改、上下架、库存/价格、分类管理、**商品图上传** | 设计稿明说占位图需替换真实图，没有图片管理则商品无法露出 |
| 订单管理 | 查询/详情、发货（物流单号 + 微信发货录入接口）、取消/改价、导出 | 支撑「待发货→待收货」流转 |
| 售后处理 | 退款/退货审核、微信退款调用 | C 端有「退款/售后」入口；**注意设计稿未画售后流程页，C 端也要补** |
| 批发申请审核 | 列表、查看执照/门店照、通过/驳回、通知 | 设计只有提交端，没有审核端这个 Tab 就是死流程 |
| 运营位管理 | 首页轮播、精选好物、热销排序 | 当前 hardcode 在前端 |
| 用户管理 | 查询、封禁、备注 | 基础风控 |
| 系统设置 | 运费规则、管理员账号与 RBAC | 确认订单页金额=商品价，运费规则缺失 |

### P1 — 上线后尽快

- **数据看板**：GMV/订单量/支付转化率/商品销售排行。
- **优惠券管理**：创建、发放、核销统计（营销 P1 的后台侧）。
- **评价管理**：设计稿有「待评价」状态但**没有评价页面**——需要产品决策：
  要么补 C 端评价流程 + 后台审核，要么砍掉「待评价」入口。
- **会员/积分规则配置**、操作审计日志。

### 设计稿遗留的 C 端缺口（顺带评估）

1. **订单详情页缺失**——列表就是全部信息，取消订单/去支付/查物流没有落点，建议补。
2. **支付环节缺失**——提交订单直接「待付款」，需插入拉起微信支付 + 支付结果页。
3. 「任务中心」「赠品」「会员中心」「钱包」均为死链接，见下节营销评估。
4. 「客服」按钮无动作——建议直接用小程序 `button open-type="contact"` 接微信客服，零后端成本。
5. 「分享」无动作——接 `onShareAppMessage` + 后端生成分享卡片图，低成本高价值。

---

## 5. 营销功能评估（设计稿已露出 UI 钩子）

「我的」页资产条（余额/积分/卡/优惠券/钱包）+ 会员中心 + 任务中心 + 赠品，以及确认订单页「优惠券」行，说明产品规划里有完整营销体系。逐项评估：

| 功能 | 设计稿钩子 | 评估 | 建议优先级 |
|---|---|---|---|
| 优惠券 | 确认订单「暂无可用」、我的「优惠券/码」 | 电商标配，下单链路已预留位置，改造成本低：券模板 + 用户券 + 试算核销 | **P1（第一个做）** |
| 积分 | 我的「积分」 | 购物/任务得积分，抵现或兑礼；规则简单先行（1元=1分） | P1 |
| 会员体系 | 「会员中心」「成为会员」「会员码」 | 免费等级制起步（消费额升级+会员价/生日券）；会员码=线下核销身份码，若无门店场景可后置 | P1~P2 |
| 任务中心 | 菜单项 | 签到/浏览/分享任务发积分或券，依赖积分先落地 | P2 |
| 赠品 | 菜单项 | 满赠/积分兑换，依赖订单促销引擎 | P2 |
| 余额/钱包 | 资产条 | **谨慎**：预付费涉及合规（单用途预付卡监管）与微信支付协议，投入产出低，建议后置甚至砍掉，UI 先隐藏 | P3/砍 |
| 分享裂变 | 商详「分享」 | 第一步纯分享卡片（零风险）；带返佣的分销体系涉及微信「二级分销」红线，若做需严格控制在两级以内并过法务 | 分享 P1，分销 P3 |
| 新客礼 | 无 | 设计稿没有但强烈建议：注册发首单券，成本低转化明显 | P1 |
| 订阅消息 | 无 | 催付/发货/售后/批发审核结果通知，微信生态标配 | P1 |
| 促销活动 | 无 | 满减/限时价，需要订单金额试算引擎支持（preview 接口内聚），先支持单品直降+满减即可 | P2 |

营销相关表（P1 部分）：

```
coupon          id, name, type(满减/折扣), threshold, amount, scope(全场/分类/商品),
                valid_type(固定/领取后N天), valid_from/to, total, taken, per_user_limit, status
user_coupon     id, user_id, coupon_id, status(未用/已用/过期), used_order_id, expired_at
points_log      id, user_id, change, balance_after, reason(下单/签到/兑换), ref_id, created_at
member_level    id, name, min_spend, benefits(JSON)
```

金额试算统一收口在 `POST /orders/preview`：商品小计 → 促销 → 优惠券 → 积分抵扣 → 运费 → 应付，后续每加一种营销手段只改这一处。

---

## 6. 微信生态与合规清单

- [ ] 小程序类目：服装/户外用品电商类目 + 微信支付商户号
- [ ] 支付：JSAPI 下单/回调/退款 + 对账单拉取
- [ ] **发货信息录入 API**（微信对电商小程序的强制要求）
- [ ] 订阅消息模板：催付、发货、售后进度、批发审核结果
- [ ] 内容安全：昵称/备注/评价 `msgSecCheck`，头像/执照/晒图 `imgSecCheck`
- [ ] 隐私协议 + 用户协议；「个性化推荐」开关需真实生效（推荐接口按 `reco_enabled` 降级为默认排序）
- [ ] 营业执照等敏感图片：私有读存储桶 + 临时签名 URL，仅管理端可看

---

## 7. 实施分期建议

| 阶段 | 范围 | 结果 |
|---|---|---|
| **一期（MVP，可收款）** | 登录/商品/购物车/订单/微信支付/地址/发货 + 管理后台 P0（商品、订单、售后、批发审核、运营位、运费） | 前端去 mock，真实交易闭环 |
| **二期（营销起步）** | 优惠券 + 新客礼 + 积分 + 订阅消息 + 分享卡片 + 数据看板；补 C 端订单详情/售后/评价页 | 拉新促活基础盘 |
| **三期（体系化）** | 会员等级 + 任务中心 + 赠品/满减促销引擎 | 复购运营 |
| **远期（视业务）** | 批发 B2B 在线下单、分销裂变、钱包（若合规通过） | 第二增长曲线 |

---

## 8. 前端改造点（接入后端时）

1. `utils/data.js` 替换为 API 请求层（`wx.request` 封装：token 注入、401 重登、错误 toast）。
2. `app.js` globalData 改为「服务端为准 + 本地缓存兜底」。
3. 提交订单后插入微信支付流程与支付结果页。
4. `prod-img` 组件替换为真实 `<image>`（SKU 图），占位组件保留为加载兜底。
5. 「客服」接 `open-type="contact"`；「分享」接 `onShareAppMessage`。
6. 地址表单升级省市区选择器；确认订单页优惠券行接可用券列表。
