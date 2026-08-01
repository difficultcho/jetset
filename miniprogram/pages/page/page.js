const app = getApp();
const api = require('../../utils/api.js');
const { toPageBlocks } = require('../../utils/mapper.js');

// 通用内容页外壳：加载任意配置化页面（key），交给 page-blocks 渲染
Page({
  data: { blocks: [], heroH: 600 },

  onLoad(opts) {
    this.setData({ heroH: app.refreshMetrics().heroH });
    this.key = opts.key || '';
    this.fetch();
  },

  // 折叠屏展开/收起、分屏会改变窗口尺寸，撑满首屏图的高度需重算
  onResize() { this.setData({ heroH: app.refreshMetrics().heroH }); },

  async fetch() {
    try {
      const page = await api.page(this.key);
      if (!page) return wx.showToast({ title: '内容不存在', icon: 'none' });
      wx.setNavigationBarTitle({ title: page.title || 'JET SET' });
      this.setData({ blocks: toPageBlocks(page.blocks) });
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' });
    }
  },

  onHide() {
    const c = this.selectComponent('#blocks');
    if (c) c.pauseVideos();
  }
});
