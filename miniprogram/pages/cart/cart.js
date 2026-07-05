const app = getApp();
const api = require('../../utils/api.js');
const { toCartItem, toProd } = require('../../utils/mapper.js');
const { toastError } = require('../../utils/request.js');

Page({
  data: {
    sbh: 20,
    items: [],
    sel: [],
    editing: false,
    total: 0,
    allSel: false,
    recs: []
  },

  onLoad() {
    this.setData({ sbh: app.globalData.statusBarHeight });
  },

  onShow() {
    this.tb();
    this.load();
  },

  tb() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(2);
  },

  async load() {
    try {
      const raw = await api.cartList();
      app.globalData.cartCount = raw.reduce((s, i) => s + i.qty, 0);
      this.tb();
      const items = raw.map(toCartItem);
      const sel = items.map(() => true);
      this.setData(
        { items, sel, editing: items.length ? this.data.editing : false },
        () => this.calc()
      );
      // 推荐位：不在购物车中的商品
      const page = await api.products({ page_size: 12 });
      const inCart = {};
      raw.forEach((r) => { inCart[r.spu_id] = true; });
      this.setData({ recs: page.items.filter((p) => !inCart[p.id]).slice(0, 4).map(toProd) });
    } catch (e) {
      toastError(e);
    }
  },

  calc() {
    const { items, sel } = this.data;
    const total = items.reduce((s, it, i) => s + (sel[i] ? it.price * it.qty : 0), 0);
    this.setData({ total, allSel: sel.length > 0 && sel.every(Boolean) });
  },

  toggleEdit() {
    this.setData({ editing: !this.data.editing });
  },

  toggleSel(e) {
    const i = e.currentTarget.dataset.i;
    this.setData({ ['sel[' + i + ']']: !this.data.sel[i] }, () => this.calc());
  },

  toggleAll() {
    const v = !this.data.allSel;
    this.setData({ sel: this.data.items.map(() => v) }, () => this.calc());
  },

  async chQty(e) {
    const { i, d } = e.currentTarget.dataset;
    const item = this.data.items[i];
    const qty = Math.max(1, item.qty + d);
    if (qty === item.qty) return;
    try {
      await api.cartPatch(item.id, qty);
      this.setData({ ['items[' + i + '].qty']: qty }, () => this.calc());
      app.globalData.cartCount = this.data.items.reduce((s, it) => s + it.qty, 0);
      this.tb();
    } catch (err) {
      toastError(err);
    }
  },

  async del(e) {
    const i = e.currentTarget.dataset.i;
    try {
      await api.cartDelete(this.data.items[i].id);
      await this.load();
    } catch (err) {
      toastError(err);
    }
  },

  checkout() {
    const { items, sel } = this.data;
    const chosen = items.filter((_, i) => sel[i]);
    if (!chosen.length) {
      wx.showToast({ title: '请选择商品', icon: 'none' });
      return;
    }
    app.globalData.pendingOrder = {
      items: chosen.map((it) => ({ sku_id: it.skuId, qty: it.qty })),
      from: 'cart',
      cartItemIds: chosen.map((it) => it.id)
    };
    wx.navigateTo({ url: '/pages/order-confirm/order-confirm' });
  },

  goShop() {
    wx.switchTab({ url: '/pages/shop/shop' });
  }
});
