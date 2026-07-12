const api = require('../../utils/api.js');

const REASONS = ['订单款式错误', '订单数量错误', '改变主意', '订单信息填写错误', '与门店导购协商一致'];

Page({
  data: { reasons: REASONS, idx: 2, submitting: false },
  onLoad(opts) { this.id = opts.id; },
  pick(e) { this.setData({ idx: e.currentTarget.dataset.i }); },
  async submit() {
    if (this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      await api.orderCancel(this.id);
      wx.showToast({ title: '订单已取消', icon: 'none' });
      setTimeout(() => {
        const pages = getCurrentPages();
        wx.navigateBack({ delta: Math.min(2, pages.length - 1) });
      }, 700);
    } catch (e) {
      wx.showToast({ title: (e && e.message) || '取消失败', icon: 'none' });
      this.setData({ submitting: false });
    }
  }
});
