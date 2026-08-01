const app = getApp();
const api = require('../../utils/api.js');
const { toPageBlocks } = require('../../utils/mapper.js');

const PAGE_CACHE = 'page_home_blocks';

// 首页 tab = 挂载 page(key='home')，块渲染交给 page-blocks 组件
Page({
  data: { sbh: 20, heroH: 600, bagCount: 0, scrollTop: 0, blocks: [] },

  onLoad() {
    this.setData(app.refreshMetrics());
    // 先用上次的块秒开，取数交给 onShow（它在 onLoad 之后必然触发，不必在此重复请求）
    const cached = wx.getStorageSync(PAGE_CACHE);
    if (cached && cached.length) this.setData({ blocks: toPageBlocks(cached) });
  },

  // 折叠屏展开/收起、分屏会改变窗口尺寸，几何需重算（内容取数不受影响）
  onResize() { this.setData(app.refreshMetrics()); },

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
    // tab 页 onLoad 只跑一次，取数必须放 onShow，否则后台改了配置要杀应用才能看到
    this.fetch();
  },

  scrollToTop() { this.setData({ scrollTop: this.data.scrollTop === 0 ? 1 : 0 }); },
  goBag() { wx.navigateTo({ url: '/pages/bag/bag' }); },
  goSearch() { wx.navigateTo({ url: '/pages/search/search' }); }
});
