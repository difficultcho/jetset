const app = getApp();
const api = require('../../utils/api.js');
const { toOrderLine, toAddress, fmt } = require('../../utils/mapper.js');

Page({
  data: {
    lines: [],
    itemText: '0',
    payText: '0',
    addr: null,
    packaging: 'classic',
    agree: false,
    submitting: false
  },

  onLoad() {
    const po = app.globalData.pendingOrder;
    if (!po || !po.items || !po.items.length) { wx.navigateBack(); return; }
    this.po = po;
    this.loadPreview();
  },

  async onShow() {
    try {
      const list = await api.addresses();
      let addr = null;
      if (app.globalData.pickedAddrId) {
        const found = list.find((a) => a.id === app.globalData.pickedAddrId);
        if (found) addr = toAddress(found);
      }
      if (!addr && list.length) addr = toAddress(list[0]);
      this.setData({ addr });
    } catch (e) { /* 静默 */ }
  },

  async loadPreview() {
    try {
      const d = await api.orderPreview(this.po.items);
      this.setData({
        lines: d.items.map(toOrderLine),
        itemText: fmt(d.item_amount),
        payText: fmt(d.pay_amount)
      });
    } catch (e) { wx.showToast({ title: '加载失败', icon: 'none' }); }
  },

  goAddress() { wx.navigateTo({ url: '/pages/addresses/addresses?select=1' }); },
  pickPackaging(e) { this.setData({ packaging: e.currentTarget.dataset.p }); },
  toggleAgree() { this.setData({ agree: !this.data.agree }); },

  async submit() {
    if (this.data.submitting) return;
    if (!this.data.addr) return wx.showToast({ title: '请选择收货地址', icon: 'none' });
    if (!this.data.agree) return wx.showToast({ title: '请阅读并同意销售条款', icon: 'none' });
    this.setData({ submitting: true });
    try {
      const order = await api.orderCreate(this.po.items, this.data.addr.id, '');
      if (this.po.from === 'cart' && this.po.cartItemIds) {
        for (const id of this.po.cartItemIds) {
          try { await api.cartDelete(id); } catch (e) { /* 忽略 */ }
        }
      }
      await app.refreshCartCount();
      app.globalData.pendingOrder = null;
      app.globalData.pickedAddrId = null;
      wx.redirectTo({ url: '/pages/payment/payment?id=' + order.id });
    } catch (e) {
      wx.showToast({ title: (e && e.message) || '提交失败', icon: 'none' });
      this.setData({ submitting: false });
    }
  }
});
