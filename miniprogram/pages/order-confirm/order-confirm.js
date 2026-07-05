const app = getApp();
const api = require('../../utils/api.js');
const { toOrderLine, toAddress, fen2yuan } = require('../../utils/mapper.js');
const { toastError } = require('../../utils/request.js');

Page({
  data: {
    lines: [],
    addr: null,
    note: '',
    itemAmount: 0,
    payAmount: 0,
    submitting: false
  },

  onLoad() {
    const po = app.globalData.pendingOrder;
    if (!po || !po.items || !po.items.length) {
      wx.navigateBack();
      return;
    }
    this.po = po;
    this.loadPreview();
  },

  async onShow() {
    try {
      const list = await api.addresses();
      this.setData({ addr: list.length ? toAddress(list[0]) : null });
    } catch (e) {
      toastError(e);
    }
  },

  async loadPreview() {
    try {
      const d = await api.orderPreview(this.po.items);
      this.setData({
        lines: d.items.map(toOrderLine),
        itemAmount: fen2yuan(d.item_amount),
        payAmount: fen2yuan(d.pay_amount)
      });
    } catch (e) {
      toastError(e);
    }
  },

  chQty(e) {
    const { i, d } = e.currentTarget.dataset;
    const qty = Math.max(1, this.po.items[i].qty + d);
    if (qty === this.po.items[i].qty) return;
    this.po.items[i].qty = qty;
    this.loadPreview();
  },

  onNote(e) {
    this.setData({ note: e.detail.value });
  },

  goAddress() {
    wx.navigateTo({ url: '/pages/address/address' });
  },

  async submit() {
    if (this.data.submitting) return;
    if (!this.data.addr) {
      wx.showToast({ title: '请先添加收货地址', icon: 'none' });
      return;
    }
    this.setData({ submitting: true });
    try {
      await api.orderCreate(this.po.items, this.data.addr.id, this.data.note);
      // 购物车结算的商品下单后移出购物车
      if (this.po.from === 'cart' && this.po.cartItemIds) {
        for (const id of this.po.cartItemIds) {
          try { await api.cartDelete(id); } catch (e) { /* 单条失败忽略 */ }
        }
      }
      await app.refreshCartCount();
      app.globalData.pendingOrder = null;
      wx.switchTab({ url: '/pages/mine/mine' });
    } catch (e) {
      toastError(e);
      this.setData({ submitting: false });
    }
  }
});
