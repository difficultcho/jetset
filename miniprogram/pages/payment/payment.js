const app = getApp();
const api = require('../../utils/api.js');
const { fmt } = require('../../utils/mapper.js');

Page({
  data: { order: null, payText: '0', method: 'wechat', countdown: '', paying: false },

  onLoad(opts) {
    this.id = opts.id;
    this.load();
  },

  async load() {
    try {
      const o = await api.orderDetail(this.id);
      this.setData({ order: o, payText: fmt(o.pay_amount) });
      this.startCountdown(o.expire_at);
    } catch (e) { wx.showToast({ title: '订单加载失败', icon: 'none' }); }
  },

  startCountdown(expireAt) {
    if (!expireAt) return;
    const deadline = new Date(expireAt.replace(' ', 'T')).getTime();
    const tick = () => {
      const left = Math.max(0, deadline - Date.now());
      const m = Math.floor(left / 60000);
      const s = Math.floor((left % 60000) / 1000);
      const pad = (n) => ('0' + n).slice(-2);
      this.setData({ countdown: '00 : ' + pad(m) + ' : ' + pad(s) });
      if (left <= 0) clearInterval(this.iv);
    };
    tick();
    this.iv = setInterval(tick, 1000);
  },
  onUnload() { clearInterval(this.iv); },

  pickMethod(e) { this.setData({ method: e.currentTarget.dataset.m }); },

  async pay() {
    if (this.data.paying) return;
    this.setData({ paying: true });
    try {
      await api.orderPay(this.id);
      await api.mockPayConfirm(this.data.order.order_no);
      wx.showToast({ title: '支付成功（演示）', icon: 'none' });
      setTimeout(() => wx.redirectTo({ url: '/pages/order-detail/order-detail?id=' + this.id }), 800);
    } catch (e) {
      wx.showToast({ title: (e && e.message) || '支付失败', icon: 'none' });
      this.setData({ paying: false });
    }
  }
});
