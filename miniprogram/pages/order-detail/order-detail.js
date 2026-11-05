const api = require('../../utils/api.js');
const { toOrder, fmt, parseUtcMs } = require('../../utils/mapper.js');

Page({
  data: { order: null, countdown: '', pending: false, awaiting: false, confirming: false },

  onLoad(opts) { this.id = opts.id; },
  onShow() { this.load(); },
  onUnload() { clearInterval(this.iv); },

  async load() {
    try {
      const raw = await api.orderDetail(this.id);
      const order = toOrder(raw);
      order.payText = fmt(raw.pay_amount);
      this.setData({
        order,
        pending: order.status === 'pending_payment',
        awaiting: order.status === 'pending_receipt',
        confirming: false,
      });
      clearInterval(this.iv);
      if (order.status === 'pending_payment') this.startCountdown(raw.expire_at);
    } catch (e) { wx.showToast({ title: '加载失败', icon: 'none' }); }
  },

  startCountdown(expireAt) {
    const deadline = parseUtcMs(expireAt);
    if (!deadline) return;
    const pad = (n) => ('0' + n).slice(-2);
    const tick = () => {
      const left = Math.max(0, deadline - Date.now());
      const h = Math.floor(left / 3600000);
      const m = Math.floor((left % 3600000) / 60000);
      const s = Math.floor((left % 60000) / 1000);
      this.setData({ countdown: pad(h) + ' : ' + pad(m) + ' : ' + pad(s) });
      if (left <= 0) { clearInterval(this.iv); this.load(); }
    };
    tick();
    this.iv = setInterval(tick, 1000);
  },

  copyNo() {
    wx.setClipboardData({ data: this.data.order.orderNo, success: () => wx.showToast({ title: '订单号已复制', icon: 'none' }) });
  },
  copyTrack() {
    const s = this.data.order && this.data.order.shipment;
    if (!s || !s.tracking_no) return;
    wx.setClipboardData({ data: s.tracking_no, success: () => wx.showToast({ title: '运单号已复制', icon: 'none' }) });
  },
  goCancel() { wx.navigateTo({ url: '/pages/cancel/cancel?id=' + this.id }); },
  goPay() { wx.navigateTo({ url: '/pages/payment/payment?id=' + this.id }); },

  confirmReceipt() {
    if (this.data.confirming) return;
    wx.showModal({
      title: '确认收货',
      content: '确认已收到商品？',
      success: async (r) => {
        if (!r.confirm) return;
        this.setData({ confirming: true });
        try {
          await api.orderConfirm(this.id);
          wx.showToast({ title: '已确认收货', icon: 'none' });
          this.load();
        } catch (err) {
          wx.showToast({ title: (err && err.message) || '确认失败', icon: 'none' });
          this.setData({ confirming: false });
        }
      }
    });
  }
});
