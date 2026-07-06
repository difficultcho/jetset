const app = getApp();
const api = require('../../utils/api.js');
const { toOrderLine, toAddress, toCoupon, fen2yuan } = require('../../utils/mapper.js');
const { toastError } = require('../../utils/request.js');

Page({
  data: {
    lines: [],
    addr: null,
    note: '',
    itemAmount: 0,
    payAmount: 0,
    discount: 0,
    coupons: [],
    usableCount: 0,
    appliedId: null,
    couponSheet: false,
    usePoints: false,
    pointsAvailable: 0,
    pointsUsed: 0,
    pointsDeduct: 0,
    submitting: false
  },

  onLoad() {
    const po = app.globalData.pendingOrder;
    if (!po || !po.items || !po.items.length) {
      wx.navigateBack();
      return;
    }
    this.po = po;
    this.autoPicked = false;
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
      const d = await api.orderPreview(this.po.items, this.data.appliedId, this.data.usePoints);
      // 首次进入自动应用减免最大的可用券（后端已按减免额降序）
      if (!this.autoPicked) {
        this.autoPicked = true;
        const best = d.coupons.find((c) => c.usable);
        if (best) {
          this.setData({ appliedId: best.id });
          return this.loadPreview();
        }
      }
      this.setData({
        lines: d.items.map(toOrderLine),
        itemAmount: fen2yuan(d.item_amount),
        payAmount: fen2yuan(d.pay_amount),
        discount: fen2yuan(d.discount_amount),
        coupons: d.coupons.map(toCoupon),
        usableCount: d.coupons.filter((c) => c.usable).length,
        pointsAvailable: d.points_available,
        pointsUsed: d.points_used,
        pointsDeduct: fen2yuan(d.points_deduct)
      });
    } catch (e) {
      // 改数量后可能不再满足已选券门槛：清掉券重试一次
      if (this.data.appliedId) {
        this.setData({ appliedId: null });
        return this.loadPreview();
      }
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

  openCoupons() {
    if (!this.data.coupons.length) {
      wx.showToast({ title: '暂无优惠券', icon: 'none' });
      return;
    }
    this.setData({ couponSheet: true });
  },

  closeCoupons() {
    this.setData({ couponSheet: false });
  },

  pickCoupon(e) {
    const id = e.currentTarget.dataset.id || null; // 0/undefined = 不使用
    this.setData({ appliedId: id, couponSheet: false });
    this.loadPreview();
  },

  togglePoints(e) {
    this.setData({ usePoints: e.detail.value });
    this.loadPreview();
  },

  noop() {},

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
      await api.orderCreate(this.po.items, this.data.addr.id, this.data.note,
        this.data.appliedId, this.data.usePoints);
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
