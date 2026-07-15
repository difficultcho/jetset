const app = getApp();
const api = require('../../utils/api.js');
const { toDetail, toCard } = require('../../utils/mapper.js');

Page({
  data: {
    sbh: 20,
    prod: null,
    ci: 0,
    size: '',
    acc: { d: true, s: false, c: false },
    wished: false,
    recs: []
  },

  async onLoad(opts) {
    this.setData({ sbh: app.globalData.statusBarHeight });
    this.pid = opts.id;
    app.pushFootprint(opts.id);
    try {
      const d = await api.productDetail(opts.id);
      const prod = toDetail(d);
      this.setData({
        prod,
        ci: 0,
        size: prod.sizes[0] || '',
        wished: app.isWished(opts.id)
      });
      // 推荐取材：同品类按销量优先（看裤子推热卖的裤子），不足补精选
      const page = await api.products({ cat: d.category, sort: 'sales', page_size: 6 });
      let recs = page.items.filter((p) => p.id !== d.id);
      if (recs.length < 2) {
        const extra = await api.products({ featured: 1, sort: 'sales', page_size: 6 });
        extra.items.forEach((p) => {
          if (p.id !== d.id && !recs.some((r) => r.id === p.id)) recs.push(p);
        });
      }
      this.setData({ recs: recs.slice(0, 2).map(toCard) });
    } catch (e) {
      wx.showToast({ title: '商品加载失败', icon: 'none' });
    }
  },

  onShow() {
    const f = this.selectComponent('#fab');
    if (f) f.refresh();
  },

  // 右滑返回
  onTS(e) { this.t = { x: e.touches[0].clientX, y: e.touches[0].clientY }; },
  onTE(e) {
    if (!this.t) return;
    const dx = e.changedTouches[0].clientX - this.t.x;
    const dy = e.changedTouches[0].clientY - this.t.y;
    if (dx > 80 && Math.abs(dy) < 60) wx.navigateBack();
  },

  goBack() {
    const pages = getCurrentPages();
    if (pages.length > 1) wx.navigateBack();
    else wx.switchTab({ url: '/pages/shop/shop' });
  },

  pickColor(e) { this.setData({ ci: e.currentTarget.dataset.i }); },
  pickSize(e) { this.setData({ size: e.currentTarget.dataset.s }); },
  toggleAcc(e) {
    const k = e.currentTarget.dataset.k;
    this.setData({ ['acc.' + k]: !this.data.acc[k] });
  },

  _sku() {
    const p = this.data.prod;
    return (p.skus || []).find((s) => s.color_index === this.data.ci && s.size === this.data.size);
  },

  async addBag() {
    const sku = this._sku();
    if (!sku) return wx.showToast({ title: '该规格暂不可选', icon: 'none' });
    if (sku.stock < 1) return wx.showToast({ title: '该规格缺货', icon: 'none' });
    try {
      await api.cartAdd(sku.id, 1);
      await app.refreshCartCount();
      const f = this.selectComponent('#fab');
      if (f) f.refresh();
      wx.showToast({ title: '已加入购物袋', icon: 'none' });
    } catch (err) {
      wx.showToast({ title: (err && err.message) || '加入失败', icon: 'none' });
    }
  },

  buyNow() {
    const sku = this._sku();
    if (!sku) return wx.showToast({ title: '该规格暂不可选', icon: 'none' });
    if (sku.stock < 1) return wx.showToast({ title: '该规格缺货', icon: 'none' });
    app.globalData.pendingOrder = { items: [{ sku_id: sku.id, qty: 1 }], from: 'buy' };
    wx.navigateTo({ url: '/pages/confirm/confirm' });
  },

  toggleWish() {
    const added = app.toggleWish(this.pid);
    this.setData({ wished: added });
    wx.showToast({ title: added ? '已加入心愿单' : '已移出心愿单', icon: 'none' });
  },

  goPdp(e) { wx.redirectTo({ url: '/pages/pdp/pdp?id=' + e.detail.id }); },
  goSizeGuide() { wx.navigateTo({ url: '/pages/size-guide/size-guide' }); }
});
