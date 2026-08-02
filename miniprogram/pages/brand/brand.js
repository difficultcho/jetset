const app = getApp();
const api = require('../../utils/api.js');
const { toPageBlocks } = require('../../utils/mapper.js');

const PAGE_CACHE = 'page_brand_blocks';

// 「关于品牌」tab = 挂载 page(key='brand')，块渲染交给 page-blocks 组件
Page({
  data: { sbh: 20, heroH: 600, blocks: [] },

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
      const page = await api.page('brand');
      // 页面未配置/被停用时接口返回 null：必须清掉本地缓存并置空，
      // 否则秒开缓存会一直显示已经不存在的旧内容
      const blocks = (page && page.blocks) || [];
      wx.setStorageSync(PAGE_CACHE, blocks);
      this.setData({ blocks: toPageBlocks(blocks) });
    } catch (e) { /* 静默，保留缓存 */ }
  },

  onHide() {
    const c = this.selectComponent('#blocks');
    if (c) c.pauseVideos();
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(1);
    app.refreshCartCount();
    // tab 页 onLoad 只跑一次，取数必须放 onShow，否则后台改了配置要杀应用才能看到
    this.fetch();
  }
});
