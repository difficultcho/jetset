const api = require('../../utils/api.js');
const { toCard, toBrand } = require('../../utils/mapper.js');

Page({
  data: { post: null, prods: [] },
  async onLoad() {
    try {
      const p = await api.brandFirst('campaign');
      if (p) this.setData({ post: toBrand(p) });
      const page = await api.products({ page_size: 4 });
      this.setData({ prods: page.items.slice(0, 3).map(toCard) });
    } catch (e) { /* 静默 */ }
  },
  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.currentTarget.dataset.id }); }
});
