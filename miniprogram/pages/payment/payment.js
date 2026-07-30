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
      // 渠道由后端 MOCK_MODE 决定，前端按返回的 provider 分支，
      // 不能硬编码假支付——否则后端切了真实支付，这里还在打 mock 端点
      const pay = await api.orderPay(this.id);
      if (pay && pay.provider === 'mock') {
        await api.mockPayConfirm(pay.order_no);
        wx.showToast({ title: '支付成功（演示）', icon: 'none' });
      } else {
        await this._wxPay(pay);
        wx.showToast({ title: '支付成功', icon: 'none' });
      }
      setTimeout(() => wx.redirectTo({ url: '/pages/order-detail/order-detail?id=' + this.id }), 800);
    } catch (e) {
      // 用户主动取消收银台不算失败，静默回到可支付状态
      const msg = (e && (e.errMsg || e.message)) || '支付失败';
      if (msg.indexOf('cancel') < 0) wx.showToast({ title: msg, icon: 'none' });
      this.setData({ paying: false });
    }
  },

  // 真实微信支付：后端返回 wx.requestPayment 所需的下单参数
  _wxPay(p) {
    return new Promise((resolve, reject) => {
      wx.requestPayment({
        timeStamp: p.timeStamp, nonceStr: p.nonceStr, package: p.package,
        signType: p.signType || 'RSA', paySign: p.paySign,
        success: resolve, fail: reject
      });
    });
  }
});
