const app = getApp();
const api = require('../../utils/api.js');
const { toPageBlocks } = require('../../utils/mapper.js');

const PAGE_CACHE = 'page_home_blocks';

// 首页 tab = 挂载 page(key='home')，块渲染交给 page-blocks 组件
Page({
  data: { sbh: 20, heroH: 600, bagCount: 0, scrollTop: 0, blocks: [] },

  onLoad() {
    const sbh = app.globalData.statusBarHeight;
    const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    const heroH = win.windowHeight - sbh - Math.round((win.windowWidth * 88) / 750);
    this.setData({ sbh, heroH });
    const cached = wx.getStorageSync(PAGE_CACHE);
    if (cached && cached.length) this.setData({ blocks: toPageBlocks(cached) });
    this.fetch();
  },

  async fetch() {
    try {
      const page = await api.page('home');
      if (page && page.blocks) {
        wx.setStorageSync(PAGE_CACHE, page.blocks);
        this.setData({ blocks: toPageBlocks(page.blocks) });
      }
    } catch (e) { console.error('[home] 取数失败：', e && e.message); }
  },

  onHide() { const c = this.selectComponent('#blocks'); if (c) c.pauseVideos(); },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(0);
    app.refreshCartCount().then((c) => this.setData({ bagCount: c }));
    if (!this.data.blocks.length) this.fetch();
  },

  scrollToTop() { this.setData({ scrollTop: this.data.scrollTop === 0 ? 1 : 0 }); },
  goBag() { wx.navigateTo({ url: '/pages/bag/bag' }); },
  goSearch() { wx.navigateTo({ url: '/pages/search/search' }); }
});
