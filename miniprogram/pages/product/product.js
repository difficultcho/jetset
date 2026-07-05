const app = getApp();
const api = require('../../utils/api.js');
const { toDetail } = require('../../utils/mapper.js');
const { toastError } = require('../../utils/request.js');

Page({
  data: { prod: null, ci: 0, modal: '', sbh: 20 },

  async onLoad(options) {
    this.setData({ sbh: app.globalData.statusBarHeight });
    try {
      const d = await api.productDetail(options.id);
      this.setData({ prod: toDetail(d) });
    } catch (e) {
      toastError(e);
    }
  },

  // 右滑手势返回（设计稿：详情页无返回箭头，dx > 80 且 |dy| < 60 时返回）
  onTS(e) {
    this.t = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  },
  onTE(e) {
    if (!this.t) return;
    const dx = e.changedTouches[0].clientX - this.t.x;
    const dy = e.changedTouches[0].clientY - this.t.y;
    if (dx > 80 && Math.abs(dy) < 60) wx.navigateBack();
  },

  pickColor(e) {
    this.setData({ ci: e.currentTarget.dataset.i });
  },

  openModal(e) {
    this.setData({ modal: e.currentTarget.dataset.mode });
  },

  closeModal() {
    this.setData({ modal: '' });
  },

  async onConfirm(e) {
    const { skuId, qty } = e.detail;
    if (this.data.modal === 'cart') {
      try {
        await api.cartAdd(skuId, qty);
        this.setData({ modal: '' });
        app.refreshCartCount();
        wx.showToast({ title: '已加入购物车', icon: 'success' });
      } catch (err) {
        toastError(err);
      }
    } else {
      app.globalData.pendingOrder = { items: [{ sku_id: skuId, qty }], from: 'buy' };
      this.setData({ modal: '' });
      wx.navigateTo({ url: '/pages/order-confirm/order-confirm' });
    }
  }
});
