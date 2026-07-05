const app = getApp();
const api = require('../../utils/api.js');
const { toastError } = require('../../utils/request.js');

Page({
  data: {
    sbh: 20,
    user: {},
    cartCnt: 0,
    stats: [
      { l: '余额', v: '0.00' },
      { l: '积分', v: '0' },
      { l: '卡', v: '0' },
      { l: '优惠券/码', v: '0' },
      { l: '钱包', v: '⊙' }
    ],
    oStats: [
      { l: '待付款', n: 'pay' },
      { l: '待发货', n: 'ship' },
      { l: '待收货', n: 'truck' },
      { l: '待评价', n: 'star' },
      { l: '退款/售后', n: 'refund' }
    ]
  },

  onLoad() {
    this.setData({ sbh: app.globalData.statusBarHeight });
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(4);
    this.fetch();
  },

  async fetch() {
    try {
      const u = await api.me();
      app.globalData.userInfo = u;
      const cnt = await app.refreshCartCount();
      this.setData({
        user: u,
        cartCnt: cnt,
        'stats[1].v': String(u.points || 0)
      });
      if (typeof this.getTabBar === 'function') this.getTabBar().refresh(4);
    } catch (e) {
      toastError(e);
    }
  },

  goProfile() {
    wx.navigateTo({ url: '/pages/profile/profile' });
  },

  goOrders() {
    wx.navigateTo({ url: '/pages/orders/orders' });
  },

  goAddress() {
    wx.navigateTo({ url: '/pages/address/address' });
  },

  goCart() {
    wx.switchTab({ url: '/pages/cart/cart' });
  },

  noop() {}
});
