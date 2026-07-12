const api = require('../../utils/api.js');
const { toBrand } = require('../../utils/mapper.js');

Page({
  data: { post: null },
  async onLoad() {
    try {
      const p = await api.brandFirst('moment');
      if (p) this.setData({ post: toBrand(p) });
    } catch (e) { /* 静默 */ }
  }
});
