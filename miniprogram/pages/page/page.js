const app = getApp();
const api = require('../../utils/api.js');
const { toPageBlocks } = require('../../utils/mapper.js');

// 通用内容页外壳：加载任意配置化页面（key），交给 page-blocks 渲染
Page({
  data: { blocks: [], heroH: 600 },

  onLoad(opts) {
    const sbh = app.globalData.statusBarHeight;
    const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    // 撑满首屏图：窗口高 −（状态栏 + 88rpx 导航栏）
    this.setData({ heroH: win.windowHeight - sbh - Math.round((win.windowWidth * 88) / 750) });
    this.key = opts.key || '';
    this.fetch();
  },

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
