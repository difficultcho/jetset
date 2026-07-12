const api = require('../../utils/api.js');
const { toStore } = require('../../utils/mapper.js');

Page({
  data: { stores: [], idx: 0 },
  async onLoad() {
    try {
      const stores = await api.stores();
      this.setData({ stores: stores.map(toStore) });
    } catch (e) { /* 静默 */ }
  },
  next() {
    if (this.data.stores.length) this.setData({ idx: (this.data.idx + 1) % this.data.stores.length });
  }
});
