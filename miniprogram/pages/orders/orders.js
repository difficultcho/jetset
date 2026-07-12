const api = require('../../utils/api.js');
const { toOrder } = require('../../utils/mapper.js');

const SUBS = [
  { label: '全部', status: '' },
  { label: '待支付', status: 'pending_payment' },
  { label: '待收货', status: 'pending_receipt' },
  { label: '售后记录', status: '__after' }
];

Page({
  data: { subs: SUBS, si: 0, list: [], loaded: false },

  onShow() { this.fetch(); },

  async fetch() {
    const sub = SUBS[this.data.si];
    try {
      if (sub.status === '__after') { this.setData({ list: [], loaded: true }); return; }
      const page = await api.orders(sub.status);
      this.setData({ list: page.items.map(toOrder), loaded: true });
    } catch (e) { /* 静默 */ }
  },

  pickSub(e) { this.setData({ si: e.currentTarget.dataset.i }, () => this.fetch()); },
  goDetail(e) { wx.navigateTo({ url: '/pages/order-detail/order-detail?id=' + e.currentTarget.dataset.id }); }
});
