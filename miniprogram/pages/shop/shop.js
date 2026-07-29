const app = getApp();
const api = require('../../utils/api.js');
const nav = require('../../utils/nav.js');
const { toShopMenus } = require('../../utils/mapper.js');

Page({
  data: {
    sbh: 20,
    menus: [],       // 左菜单：上部自定义项（系列）+ 下部一级类目
    curKey: '',
    cur: null,       // 当前菜单项（含自身 filter，供「全部」入口用）
    banners: [],     // 右侧上部：图片跳链
    entries: []      // 右侧下部：下钻入口，每项就是一个商品列表过滤条件
  },

  async onLoad() {
    this.setData({ sbh: app.globalData.statusBarHeight });
    try {
      const data = await api.shop();
      const menus = toShopMenus(data.menus);
      this.setData({ menus });
      if (menus.length) this._select(menus[0]);
    } catch (e) { /* 静默：菜单为空时页面自然留白 */ }
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(2);
    app.refreshCartCount();
    const f = this.selectComponent('#fab');
    if (f) f.refresh();
  },

  pick(e) {
    const m = this.data.menus[e.currentTarget.dataset.i];
    if (m) this._select(m);
  },

  _select(m) {
    this.setData({
      curKey: m.key, cur: m,
      banners: m.banners || [],
      entries: m.entries || []
    });
  },

  goBanner(e) {
    const b = this.data.banners[e.currentTarget.dataset.i];
    if (b) nav.go(b.link);
  },

  // 下钻入口 / 当前项全部商品 —— 都落到同一个商品列表页
  goEntry(e) {
    const it = this.data.entries[e.currentTarget.dataset.i];
    if (it) nav.goList(Object.assign({}, it.filter, { title: it.title }));
  },

  goAll() {
    const m = this.data.cur;
    if (m) nav.goList(Object.assign({}, m.filter, { title: m.title }));
  },

  goSearch() { wx.navigateTo({ url: '/pages/list/list' }); }
});
