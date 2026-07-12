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
  data: { sbh: 20, registered: false, user: null, menu: MENU, code: '' },

  onLoad() { this.setData({ sbh: app.globalData.statusBarHeight }); },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(3);
    app.refreshCartCount();
    this.fetch();
  },

  async fetch() {
    try {
      const u = await api.me();
      app.globalData.userInfo = u;
      this.setData({
        user: u,
        registered: !!u.name,
        code: 'AURL' + String(100000 + (u.id || 0) * 37 % 900000).slice(0, 6)
      });
    } catch (e) { /* 静默 */ }
  },

  openJoin() { wx.navigateTo({ url: '/pages/open-card/open-card' }); },
  goProfile() { wx.navigateTo({ url: '/pages/profile/profile' }); },
  goCode() { wx.navigateTo({ url: '/pages/member-code/member-code' }); },
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
