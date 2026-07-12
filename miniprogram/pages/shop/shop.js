const app = getApp();
const api = require('../../utils/api.js');
const { toCard } = require('../../utils/mapper.js');

Page({
  data: {
    sbh: 20,
    rail: [],        // [{kind:'series'|'cat', id, en, cn, subs?}]
    curKey: '',      // 'series-1' / 'cat-3'
    card: null,      // 系列大卡
    subs: [],        // 品类二级 chips
    subCur: '',
    tiles: []
  },

  async onLoad() {
    this.setData({ sbh: app.globalData.statusBarHeight });
    try {
      const [series, cats] = await Promise.all([api.series(), api.categories()]);
      const rail = series.map((s) => ({ kind: 'series', id: s.id, en: s.en, cn: s.name, tint: s.cover_tint, subtitle: s.subtitle }))
        .concat(cats.map((c) => ({ kind: 'cat', id: c.id, en: c.en, cn: c.name, subs: c.children || [] })));
      this.setData({ rail });
      if (rail.length) this.pick({ currentTarget: { dataset: { i: 0 } } });
    } catch (e) { /* 静默 */ }
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(2);
    app.refreshCartCount();
    const f = this.selectComponent('#fab');
    if (f) f.refresh();
  },

  async pick(e) {
    const item = this.data.rail[e.currentTarget.dataset.i];
    this.setData({ curKey: item.kind + '-' + item.id });
    if (item.kind === 'series') {
      this.setData({
        card: { name: item.cn, en: item.en, subtitle: item.subtitle, tint: item.tint || '#e8dcc8', seriesId: item.id },
        subs: [], subCur: ''
      });
      await this._load({ series: item.id });
    } else {
      this.setData({
        card: null,
        subs: item.subs,
        subCur: ''
      });
      await this._load({ cat: item.cn });
    }
  },

  async pickSub(e) {
    const name = e.currentTarget.dataset.name;
    this.setData({ subCur: name });
    await this._load({ cat: name || this._curCatName() });
  },

  _curCatName() {
    const item = this.data.rail.find((r) => r.kind + '-' + r.id === this.data.curKey);
    return item ? item.cn : '';
  },

  async _load(params) {
    try {
      const page = await api.products(Object.assign({ page_size: 30 }, params));
      this.setData({ tiles: page.items.map(toCard) });
    } catch (e) { this.setData({ tiles: [] }); }
  },

  goCard() {
    const c = this.data.card;
    if (c) wx.navigateTo({ url: '/pages/list/list?series=' + c.seriesId + '&title=' + encodeURIComponent(c.en) });
  },
  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.currentTarget.dataset.id }); },
  goSearch() { wx.navigateTo({ url: '/pages/list/list' }); }
});
