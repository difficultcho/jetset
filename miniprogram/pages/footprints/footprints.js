const app = getApp();
const api = require('../../utils/api.js');
const { toCard } = require('../../utils/mapper.js');

Page({
  data: { list: [], wished: {}, loaded: false },
  onShow() { this.load(); },
  async load() {
    const ids = app.getFootprints();
    if (!ids.length) { this.setData({ list: [], loaded: true }); return; }
    try {
      const page = await api.products({ page_size: 100 });
      const byId = {};
      page.items.forEach((p) => { byId[String(p.id)] = p; });
      const list = ids.map((id) => byId[id]).filter(Boolean).map(toCard);
      const wished = {};
      app.getWishlist().forEach((id) => { wished[id] = true; });
      this.setData({ list, wished, loaded: true });
    } catch (e) { /* 静默 */ }
  },
  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.detail.id }); },
  onStar(e) {
    const added = app.toggleWish(e.detail.id);
    wx.showToast({ title: added ? '已加入心愿单' : '已移出心愿单', icon: 'none' });
    this.load();
  },
  clear() {
    wx.showModal({ title: '清空足迹', content: '确定清空浏览足迹吗？', success: (r) => {
      if (r.confirm) { app.clearFootprints(); this.load(); }
    } });
  }
});
