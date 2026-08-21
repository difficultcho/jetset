const app = getApp();
const api = require('../../utils/api.js');

const MENU = [
  { k: 'guide', label: '门店导购' },
  { k: 'addresses', label: '地址管理' },
  { k: 'nearby', label: '附近门店' },
  { k: 'coupons', label: '优惠券' },
  { k: 'points', label: '积分' },
  { k: 'settings', label: '个人设置' },
  { k: 'help', label: '帮助中心' },
  { k: 'follow', label: '关注我们' }
];

Page({
  // 没有「未注册」态：打开小程序时后端已按 openid 静默建号。
  // initial 是头像占位字母，取称呼首字，没填就用品牌首字母。
  data: { sbh: 20, user: {}, initial: 'J', menu: MENU },

  onLoad() { this.setData({ sbh: app.refreshMetrics().sbh }); },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(3);
    app.refreshCartCount();
    this.fetch();
  },

  // 折叠屏展开/收起、分屏会改变窗口尺寸，状态栏高度需重算
  onResize() { this.setData({ sbh: app.refreshMetrics().sbh }); },

  async fetch() {
    try {
      const u = await api.me();
      app.globalData.userInfo = u;
      this.setData({ user: u, initial: (u.name || 'JET SET').trim().charAt(0).toUpperCase() });
    } catch (e) { /* 静默 */ }
  },

  openJoin() { wx.navigateTo({ url: '/pages/open-card/open-card' }); },
  goProfile() { wx.navigateTo({ url: '/pages/profile/profile' }); },
  goOrders() { wx.navigateTo({ url: '/pages/orders/orders' }); },
  goBookings() { wx.navigateTo({ url: '/pages/bookings/bookings' }); },
  goWishlist() { wx.navigateTo({ url: '/pages/wishlist/wishlist' }); },
  goFootprints() { wx.navigateTo({ url: '/pages/footprints/footprints' }); },

  onMenu(e) {
    const map = {
      guide: '/pages/guide/guide', addresses: '/pages/addresses/addresses',
      nearby: '/pages/nearby/nearby', coupons: '/pages/coupons/coupons',
      points: '/pages/points/points', settings: '/pages/settings/settings',
      help: '/pages/help/help', follow: '/pages/follow/follow'
    };
    wx.navigateTo({ url: map[e.currentTarget.dataset.k] });
  }
});
