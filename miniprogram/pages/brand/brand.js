const app = getApp();
const api = require('../../utils/api.js');
const { toPageBlocks } = require('../../utils/mapper.js');

const PAGE_CACHE = 'page_brand_blocks';

// 「关于品牌」tab = 挂载 page(key='brand')，块渲染交给 page-blocks 组件
Page({
  data: { sbh: 20, heroH: 600, blocks: [] },

  onLoad() {
    const sbh = app.globalData.statusBarHeight;
    const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    this.setData({ sbh, heroH: win.windowHeight - sbh - Math.round((win.windowWidth * 88) / 750) });
    const cached = wx.getStorageSync(PAGE_CACHE);
    if (cached && cached.length) this.setData({ blocks: toPageBlocks(cached) });
    this.fetch();
  },

  async fetch() {
    try {
      const page = await api.page('brand');
      if (page && page.blocks) {
        wx.setStorageSync(PAGE_CACHE, page.blocks);
        this.setData({ blocks: toPageBlocks(page.blocks) });
      }
    } catch (e) { /* 静默，保留缓存 */ }
  },

  onHide() {
    const c = this.selectComponent('#blocks');
    if (c) c.pauseVideos();
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(1);
    app.refreshCartCount();
  }
});
