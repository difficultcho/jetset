const { ensureLogin } = require('./utils/request.js');
const api = require('./utils/api.js');

App({
  globalData: {
    statusBarHeight: 20,
    userInfo: null,   // 服务端 /me
    cartCount: 0,     // 服务端购物车数量缓存（tabBar 角标）
    pendingOrder: null // { items: [{sku_id, qty}], from: 'buy'|'cart', cartItemIds: [] }
  },

  onLaunch() {
    const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    this.globalData.statusBarHeight = win.statusBarHeight || 20;
    // 静默登录 + 拉购物车角标（失败不阻塞启动，进入页面后各自重试）
    ensureLogin()
      .then(() => this.refreshCartCount())
      .catch(() => {});
  },

  cartCount() {
    return this.globalData.cartCount;
  },

  async refreshCartCount() {
    try {
      const items = await api.cartList();
      this.globalData.cartCount = items.reduce((s, i) => s + i.qty, 0);
    } catch (e) {
      // 静默失败，角标维持旧值
    }
    return this.globalData.cartCount;
  }
});
