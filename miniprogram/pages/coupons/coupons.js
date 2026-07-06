const api = require('../../utils/api.js');
const { toCoupon } = require('../../utils/mapper.js');
const { toastError } = require('../../utils/request.js');

const TABS = [
  { label: '未使用', status: 'unused' },
  { label: '已使用', status: 'used' },
  { label: '已过期', status: 'expired' }
];

Page({
  data: {
    center: [],
    tabs: TABS.map((t) => t.label),
    ti: 0,
    mine: [],
    loaded: false
  },

  onShow() {
    this.fetch();
  },

  async fetch() {
    try {
      const [center, mine] = await Promise.all([
        api.couponsCenter(),
        api.myCoupons(TABS[this.data.ti].status)
      ]);
      this.setData({
        center: center.map(toCoupon),
        mine: mine.map(toCoupon),
        loaded: true
      });
    } catch (e) {
      toastError(e);
    }
  },

  pickTab(e) {
    this.setData({ ti: e.currentTarget.dataset.i }, () => this.fetch());
  },

  async claim(e) {
    try {
      await api.couponClaim(e.currentTarget.dataset.id);
      wx.showToast({ title: '领取成功', icon: 'success' });
      this.fetch();
    } catch (err) {
      toastError(err);
    }
  }
});
