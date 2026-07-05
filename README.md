# JETSET 户外/滑雪购物小程序

基于 `design/design_handoff_jetset_shopping_app/` 设计交接稿实现的**原生微信小程序**。

## 运行方式

1. 打开微信开发者工具
2. 「导入项目」→ 选择本仓库根目录（`project.config.json` 已配置 `miniprogramRoot: miniprogram/`）
3. AppID 使用测试号（默认 `touristappid`）即可预览

## 目录结构

```
miniprogram/
├── app.js               # 全局状态（购物车/订单/地址/用户信息）+ Storage 持久化
├── app.json             # 页面注册、自定义 tabBar 配置
├── custom-tab-bar/      # 自定义底部 Tab（线性 SVG 图标 + 购物车角标）
├── components/
│   ├── prod-img/        # 商品占位图（CSS 绘制，接入真实商品图后替换）
│   ├── atc-modal/       # 颜色/尺码选择弹窗（bottom sheet）
│   └── nav-bar/         # 自定义导航栏（购物车页/详情页使用）
├── pages/
│   ├── home/            # 首页：Hero 轮播、热销推荐、精选好物、商品网格
│   ├── shop/            # 商城：搜索 + 分类侧栏 + 商品列表 + 快捷加购
│   ├── product/         # 商品详情：色卡切换、右滑手势返回、加购/立即购买
│   ├── order-confirm/   # 确认订单：地址、数量、汇总、备注、提交
│   ├── cart/            # 购物车：勾选、编辑删除、推荐、去结算
│   ├── wholesale/       # 批发合作申请表单
│   ├── mine/            # 我的：会员头部、资产、订单入口、菜单
│   ├── orders/          # 订单列表（状态筛选 + 空状态推荐）
│   ├── address/         # 收货地址管理（新增/编辑）
│   └── profile/         # 个人信息（头像/姓名/性别/生日/地区）
└── utils/data.js        # 商品 mock 数据（接入真实 API 时替换）
```

## 前后端联调

小程序已接入后端 API（`backend/`，FastAPI）：商品/购物车/订单/地址/个人信息/批发全部走服务端，本地不再存业务数据。

联调步骤：

1. 启动后端：`cd backend && docker compose up -d`（或 venv：`.venv/bin/uvicorn app.main:app --reload`），确保已执行 `python -m app.seed`
2. 后端地址在 [miniprogram/utils/config.js](miniprogram/utils/config.js)（默认 `http://127.0.0.1:8000`）
3. **开发者工具 → 详情 → 本地设置 → 勾选「不校验合法域名」**（本地 http 联调必须）
4. 登录为静默 mock 模式（后端 `WECHAT_MOCK=true`），编译即自动登录

## 与设计稿的差异说明

- 购物车「去结算」按设计稿标注为占位交互，这里实现为真实结算流程（勾选商品 → 确认订单，下单后移出购物车）
- 同商品同规格重复加购由服务端合并数量（原型为追加新行）
- 加入购物车后增加了 Toast 反馈（详情页无 tabBar 角标可见，需要操作反馈）
- 订单列表页增加了「去支付（模拟）/取消订单/确认收货」操作按钮，用于跑通订单状态机（设计稿无支付环节）
- 商城排序 Tab（综合/销量/价格/上新）已接后端排序（设计稿为纯展示）
- 商品图为设计稿约定的 CSS 占位图案，非最终商品图（后端 SPU 图片字段已预留）
