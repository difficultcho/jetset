const app = getApp();
const api = require('../../utils/api.js');
const nav = require('../../utils/nav.js');
const { toShopMenus } = require('../../utils/mapper.js');

Page({
  data: {
    sbh: 20,
    menus: [],       // 左菜单：上部自定义项（系列）+ 下部一级类目
    curKey: '',
    cur: null,       // 当前菜单项（含自身 filter，供无下钻入口时的兜底入口用）
    banners: [],     // 右侧上部：图片跳链（可带文字标题）
    entries: []      // 右侧下部：下钻入口，每项就是一个商品列表过滤条件
  },

  onLoad() {
    this.setData({ sbh: app.refreshMetrics().sbh });
  },

  // 折叠屏展开/收起、分屏会改变窗口尺寸，状态栏高度需重算
  onResize() { this.setData({ sbh: app.refreshMetrics().sbh }); },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(2);
    app.refreshCartCount();
    const f = this.selectComponent('#fab');
    if (f) f.refresh();
    // tab 页 onLoad 只跑一次，取数必须放 onShow，否则后台改了配置要杀应用才能看到
    this.fetch();
  },

  async fetch() {
    try {
      const data = (await api.shop()) || {};
      const menus = toShopMenus(data.menus);
      this.setData({ menus });
      // 重新取数不该把用户选中的项弹回第一个；该项被删了才回落
      const keep = menus.filter((m) => m.key === this.data.curKey)[0];
      if (keep) this._select(keep);
      else if (menus.length) this._select(menus[0]);
    } catch (e) { /* 静默：菜单为空时页面自然留白 */ }
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

  // 下钻入口 —— 每项落到一个商品列表页
  goEntry(e) {
    const it = this.data.entries[e.currentTarget.dataset.i];
    if (it) nav.goList(Object.assign({}, it.filter, { title: it.title }));
  },

  // 无下钻入口时的兜底：整个菜单项的全部商品
  goAll() {
    const m = this.data.cur;
    if (m) nav.goList(Object.assign({}, m.filter, { title: m.title }));
  },

  goSearch() { wx.navigateTo({ url: '/pages/list/list' }); }
});
