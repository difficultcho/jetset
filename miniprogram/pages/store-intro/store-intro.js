const api = require('../../utils/api.js');
const { toStore } = require('../../utils/mapper.js');

Page({
  data: { stores: [] },
  async onLoad() {
    try {
      const stores = await api.stores();
      this.setData({ stores: stores.map(toStore) });
    } catch (e) { /* 静默 */ }
  },
  goDetail(e) { wx.navigateTo({ url: '/pages/store-detail/store-detail?id=' + e.currentTarget.dataset.id }); }
});
