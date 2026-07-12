const app = getApp();
const api = require('../../utils/api.js');
const { toCartItem, toCard, fmt } = require('../../utils/mapper.js');

Page({
  data: { items: [], sel: [], allSel: false, totalText: '0', recs: [] },

  onShow() { this.load(); },

  async load() {
    try {
      const raw = await api.cartList();
      app.globalData.cartCount = raw.reduce((s, i) => s + i.qty, 0);
      const items = raw.map(toCartItem);
      const sel = items.map(() => true);
      this.setData({ items, sel }, () => this.calc());
      const page = await api.products({ page_size: 12 });
      const inCart = {};
      raw.forEach((r) => { inCart[r.spu_id] = true; });
      this.setData({ recs: page.items.filter((p) => !inCart[p.id]).slice(0, 4).map(toCard) });
    } catch (e) { /* 静默 */ }
  },

  calc() {
    const { items, sel } = this.data;
    const total = items.reduce((s, it, i) => s + (sel[i] ? it.price * it.qty : 0), 0);
    this.setData({ totalText: fmt(total * 100), allSel: sel.length > 0 && sel.every(Boolean) });
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
    } catch (err) { wx.showToast({ title: '库存不足', icon: 'none' }); }
  },

  async del(e) {
    const item = this.data.items[e.currentTarget.dataset.i];
    try { await api.cartDelete(item.id); await this.load(); } catch (err) { /* 静默 */ }
  },

  wishItem(e) {
    const item = this.data.items[e.currentTarget.dataset.i];
    app.toggleWish(item.prod && item.prod.id);
    wx.showToast({ title: '已加入心愿单', icon: 'none' });
  },

  checkout() {
    const { items, sel } = this.data;
    const chosen = items.filter((_, i) => sel[i]);
    if (!chosen.length) return wx.showToast({ title: '请先勾选商品', icon: 'none' });
    app.globalData.pendingOrder = {
      items: chosen.map((it) => ({ sku_id: it.skuId, qty: it.qty })),
      from: 'cart',
      cartItemIds: chosen.map((it) => it.id)
    };
    wx.navigateTo({ url: '/pages/confirm/confirm' });
  },

  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.detail.id }); },
  goShop() { wx.switchTab({ url: '/pages/shop/shop' }); }
});
