const app = getApp();
const api = require('../../utils/api.js');
const { toCard, fullImg } = require('../../utils/mapper.js');

Page({
  data: { q: '', qDone: '', searched: false, cats: [], hot: [], results: [], wished: {} },

  async onLoad() {
    try {
      const [tree, page] = await Promise.all([
        api.categories(),
        api.products({ sort: 'sales', page_size: 10 })
      ]);
      // 叶子品类做快捷入口（无子级的一级自身算叶子）
      const leaves = [];
      tree.forEach((t) => {
        (t.children.length ? t.children : [t]).forEach((c) => leaves.push({ id: c.id, name: c.name, img: '' }));
      });
      this.setData({ cats: leaves, hot: page.items.map(toCard) });
      this.refreshWish();
      // 每个品类取第一个商品图当缩略图（cat 按名称匹配）
      const thumbs = await Promise.all(
        leaves.map((c) => api.products({ cat: c.name, page_size: 1 }).catch(() => null))
      );
      thumbs.forEach((p, i) => {
        const img = p && p.items[0] && p.items[0].image;
        if (img) this.setData({ ['cats[' + i + '].img']: fullImg(img) });
      });
    } catch (e) { /* 静默 */ }
  },

  onShow() { this.refreshWish(); },

  refreshWish() {
    const map = {};
    app.getWishlist().forEach((id) => { map[id] = true; });
    this.setData({ wished: map });
  },

  onInput(e) {
    this.setData({ q: e.detail.value });
    if (!e.detail.value) this.setData({ searched: false, results: [] });
  },

  async doSearch() {
    const q = this.data.q.trim();
    if (!q) return;
    try {
      const page = await api.products({ q, page_size: 50 });
      this.setData({ searched: true, qDone: q, results: page.items.map(toCard) });
    } catch (e) {
      wx.showToast({ title: '搜索失败，请重试', icon: 'none' });
    }
  },

  clearQ() { this.setData({ q: '', searched: false, results: [] }); },

  goCat(e) {
    const { name } = e.currentTarget.dataset;
    wx.navigateTo({ url: '/pages/list/list?cat=' + encodeURIComponent(name) + '&title=' + encodeURIComponent(name) });
  },
  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.detail.id }); },
  onStar(e) {
    const added = app.toggleWish(e.detail.id);
    this.refreshWish();
    wx.showToast({ title: added ? '已加入心愿单' : '已移出心愿单', icon: 'none' });
  },
  onBag(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.detail.id }); }
});
