const api = require('../../utils/api.js');
const { toOrder, fmt } = require('../../utils/mapper.js');

Page({
  data: { order: null, countdown: '', pending: false },

  onLoad(opts) { this.id = opts.id; },
  onShow() { this.load(); },
  onUnload() { clearInterval(this.iv); },

  async load() {
    try {
      const raw = await api.orderDetail(this.id);
      const order = toOrder(raw);
      order.payText = fmt(raw.pay_amount);
      this.setData({ order, pending: order.status === 'pending_payment' });
      clearInterval(this.iv);
      if (order.status === 'pending_payment') this.startCountdown(raw.expire_at);
    } catch (e) { wx.showToast({ title: '加载失败', icon: 'none' }); }
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
      if (left <= 0) { clearInterval(this.iv); this.load(); }
    };
    tick();
    this.iv = setInterval(tick, 1000);
  },

  copyNo() {
    wx.setClipboardData({ data: this.data.order.orderNo, success: () => wx.showToast({ title: '订单号已复制', icon: 'none' }) });
  },
  goCancel() { wx.navigateTo({ url: '/pages/cancel/cancel?id=' + this.id }); },
  goPay() { wx.navigateTo({ url: '/pages/payment/payment?id=' + this.id }); }
});
