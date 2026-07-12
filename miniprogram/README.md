# AURELLE 时尚小程序（前端）

基于 `design/design_handoff_aurelle_miniapp/` 设计交接稿实现的**原生微信小程序**。
奢侈时尚品牌美学：大面积留白、细字重、超宽字距品牌字标、黑白灰 + 暖沙色调、0.5px 细分割线。

> 沿用既有 FastAPI 后端（`backend/`）：商品/购物袋/订单/地址/会员/优惠券/积分全部走服务端。
> 按产品决策，**商品数据仍为后端现有目录**（户外品类），AURELLE 为视觉外壳；
> 品牌内容/门店/帮助/尺码表为静态数据，心愿单/足迹为本地 Storage。

## 信息架构（5 Tab + 栈式子页）

| Tab | 页面 |
|---|---|
| 首页 home | Hero 走马灯 → campaign；单品走马灯 → pdp；内容块 → list |
| 关于品牌 brand | 视频块 / projects / moments / story / storeIntro |
| 商城 shop | 左类目栏（后端分类）+ 右大卡/瓷片 → list / pdp |
| 我的 me | 未注册↔已注册；订单/预约/心愿单/足迹 + 菜单 |
| 线下门店 stores | nearby（附近门店）/ storeIntro（门店介绍）|

**购买链路**：pdp →〔即刻选购〕→ confirm → payment →（模拟支付）→ order-detail
**购物袋链路**：任意 FAB → bag →〔立即结算〕→ confirm

## 页面清单（35）

- 主 Tab：home / brand / shop / me / stores
- 商品：list（筛选抽屉 + 排序）/ pdp（尺码颜色 + 手风琴）
- 交易：bag / confirm / payment / orders / order-detail / cancel / addresses
- 会员：profile / open-card / member-code / wishlist / footprints / bookings
- 服务：settings / guide / nearby / help / help-detail / size-guide / follow
- 内容：campaign / projects / moments / story / store-intro / store-detail
- 附属：coupons / points（沿用后端营销功能，原生导航）

## 关键实现

- **设计令牌**集中在 `app.wxss`（颜色/按钮/品牌字标/占位斜纹）
- **公共组件**：`nav-bar`（子页导航）、`prod-img`（真图优先，无图暖沙斜纹占位）、
  `product-card`（网格商品卡）、`fab-stack`（客服/购物袋/回顶悬浮按钮）、`custom-tab-bar`
- **数据映射**统一在 `utils/mapper.js`（分→元千分位）；`utils/aurelle-data.js` 存门店/帮助/尺码等静态内容
- **请求层** `utils/{config,request,api}.js` 未变：静默登录、401 重试、按平台切换后端地址

## 运行

1. 微信开发者工具「导入项目」→ 仓库根目录
2. 本地联调：后端 `docker compose up -d`，开发者工具勾选「不校验合法域名」
3. 真机：`config.js` 的 `PROD` 已指向 `https://bce.kkmsee.com/jetset`

## 与设计稿的差异

- 商品为后端现有目录（户外品类），非设计稿的时尚单品；品牌视觉已全量还原
- 图片为设计稿约定的暖沙斜纹占位，接入真实摄影图后 `prod-img` 自动优先展示
- 会员"注册/开卡"映射为后端 `updateMe`（openid 静默注册，填昵称即视为已注册会员）
- 心愿单/足迹为本地 Storage；会员码/二维码为程序化绘制（演示）
