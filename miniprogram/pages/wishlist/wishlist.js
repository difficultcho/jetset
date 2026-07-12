const app = getApp();
const api = require('../../utils/api.js');
const { toCard } = require('../../utils/mapper.js');

Page({
  data: { list: [], loaded: false },
  onShow() { this.load(); },
  async load() {
    const ids = app.getWishlist();
    if (!ids.length) { this.setData({ list: [], loaded: true }); return; }
    try {
      const page = await api.products({ page_size: 100 });
      const set = {};
      ids.forEach((id) => { set[id] = true; });
      this.setData({ list: page.items.filter((p) => set[String(p.id)]).map(toCard), loaded: true });
    } catch (e) { /* 静默 */ }
  },
  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.detail.id }); },
  unStar(e) {
    app.toggleWish(e.detail.id);
    wx.showToast({ title: '已移出心愿单', icon: 'none' });
    this.load();
  },
  share() { wx.showToast({ title: '已生成分享', icon: 'none' }); }
});
