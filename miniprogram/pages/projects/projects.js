const api = require('../../utils/api.js');
const { toBrand } = require('../../utils/mapper.js');

Page({
  data: { projects: [] },
  async onLoad() {
    try {
      const posts = await api.brandPosts('project');
      this.setData({ projects: posts.map(toBrand) });
    } catch (e) { /* 静默 */ }
  }
});
