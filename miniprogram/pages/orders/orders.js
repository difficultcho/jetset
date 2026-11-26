const api = require('../../utils/api.js');
const { confirmOrder } = require('../../utils/confirm-receipt.js');
const { toOrder } = require('../../utils/mapper.js');

const SUBS = [
  { label: '全部', status: '' },
  { label: '待支付', status: 'pending_payment' },
  { label: '待收货', status: 'pending_receipt' },
  { label: '售后记录', status: '__after' }
];

Page({
  data: { subs: SUBS, si: 0, list: [], loaded: false },

  onShow() {
    if (this._waitConfirm) return;
    this.fetch();
  },

  async fetch() {
    const sub = SUBS[this.data.si];
    try {
      const status = sub.status === '__after' ? 'after_sale' : sub.status;
      const page = await api.orders(status);
      this.setData({ list: page.items.map(toOrder), loaded: true });
    } catch (e) { /* 静默 */ }
  },

  pickSub(e) { this.setData({ si: e.currentTarget.dataset.i }, () => this.fetch()); },
  goDetail(e) { wx.navigateTo({ url: '/pages/order-detail/order-detail?id=' + e.currentTarget.dataset.id }); },

  async confirmReceipt(e) {
    if (this._waitConfirm) return;
    const id = e.currentTarget.dataset.id;
    const order = (this.data.list || []).find((row) => String(row.id) === String(id));
    if (!order) return;
    this._waitConfirm = true;
    try {
      await confirmOrder(order);
      wx.showToast({ title: '已确认收货', icon: 'none' });
    } catch (err) {
      if (!(err && err.cancel)) wx.showToast({ title: (err && err.message) || '确认失败', icon: 'none' });
    } finally {
      this._waitConfirm = false;
      this.fetch();
    }
  }
});
