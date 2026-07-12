const { ensureLogin } = require('./utils/request.js');
const api = require('./utils/api.js');

App({
  globalData: {
    statusBarHeight: 20,
    navBarHeight: 44,
    userInfo: null,     // 服务端 /me
    cartCount: 0,       // 购物袋数量缓存（FAB 角标）
    pendingOrder: null  // 下单中转
  },

  onLaunch() {
    const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    this.globalData.statusBarHeight = win.statusBarHeight || 20;
    // 胶囊按钮位置推导导航栏高度
    try {
      const cap = wx.getMenuButtonBoundingClientRect();
      this.globalData.navBarHeight = (cap.top - this.globalData.statusBarHeight) * 2 + cap.height;
    } catch (e) {
      this.globalData.navBarHeight = 44;
    }
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
      // 静默失败
    }
    return this.globalData.cartCount;
  },

  // ===== 心愿单 / 足迹：本地 Storage（后端暂无，MVP 客户端持久化）=====
  getWishlist() {
    return wx.getStorageSync('wishlist') || [];
  },
  isWished(id) {
    return this.getWishlist().indexOf(String(id)) >= 0;
  },
  toggleWish(id) {
    id = String(id);
    const wl = this.getWishlist();
    const i = wl.indexOf(id);
    let added;
    if (i >= 0) { wl.splice(i, 1); added = false; }
    else { wl.push(id); added = true; }
    wx.setStorageSync('wishlist', wl);
    return added;
  },

  getFootprints() {
    return wx.getStorageSync('footprints') || [];
  },
  pushFootprint(id) {
    id = String(id);
    let fp = this.getFootprints().filter((x) => x !== id);
    fp.unshift(id);
    fp = fp.slice(0, 20);
    wx.setStorageSync('footprints', fp);
  },
  clearFootprints() {
    wx.removeStorageSync('footprints');
  }
});
