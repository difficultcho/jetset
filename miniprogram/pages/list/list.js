const app = getApp();
const api = require('../../utils/api.js');
const { toCard } = require('../../utils/mapper.js');

Page({
  data: {
    title: '全部商品',
    cat: '',
    seriesId: 0,
    q: '',
    sort: 'default',
    list: [],
    wished: {},
    filterOpen: false,
    filterExp: 0,     // 组少，进来直接展开第一组
    filters: [],     // 筛选项来自接口：尺码由库里实际值派生，价格为固定档位
    picked: {},      // 抽屉内草稿：{'size:S': true, 'price:0-199999': true}
    applied: {},     // 已生效的筛选，fetch 只认它
    pickedCount: 0
  },

  onLoad(opts) {
    const cat = opts.cat ? decodeURIComponent(opts.cat) : '';
    const seriesId = opts.series ? Number(opts.series) : 0;
    const title = opts.title ? decodeURIComponent(opts.title) : (cat || (seriesId ? '系列' : '全部商品'));
    this.setData({ cat, seriesId, title });
    this.fetch();
    this.loadFilters();
  },

  onShow() {
    this.refreshWish();
    const f = this.selectComponent('#fab');
    if (f) f.refresh();
  },

  refreshWish() {
    const wl = app.getWishlist();
    const map = {};
    wl.forEach((id) => { map[id] = true; });
    this.setData({ wished: map });
  },

  async loadFilters() {
    try {
      const data = await api.productFilters();
      this.setData({ filters: data.groups || [] });
    } catch (e) { /* 静默：拿不到筛选项则抽屉为空 */ }
  },

  // 已生效筛选 → 请求参数
  _filterParams() {
    const sizes = [];
    let price = '';
    Object.keys(this.data.applied).forEach((k) => {
      const i = k.indexOf(':');
      const g = k.slice(0, i);
      const v = k.slice(i + 1);
      if (g === 'size') sizes.push(v);
      else if (g === 'price') price = v;
    });
    const p = {};
    if (sizes.length) p.size = sizes.join(',');
    if (price) {
      const seg = price.split('-');
      p.price_min = seg[0];
      p.price_max = seg[1];
    }
    return p;
  },

  async fetch() {
    try {
      const params = Object.assign(
        { page_size: 50, sort: this.data.sort }, this._filterParams()
      );
      if (this.data.cat) params.cat = this.data.cat;
      if (this.data.seriesId) params.series = this.data.seriesId;
      if (this.data.q) params.q = this.data.q;
      const page = await api.products(params);
      this.setData({ list: page.items.map(toCard) });
      this.refreshWish();
    } catch (e) { /* 静默 */ }
  },

  onSearch(e) {
    this.setData({ q: e.detail.value });
    clearTimeout(this.t);
    this.t = setTimeout(() => this.fetch(), 300);
  },
  setSort(e) {
    this.setData({ sort: e.currentTarget.dataset.s });
    this.fetch();
  },

  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.detail.id }); },
  onStar(e) {
    const added = app.toggleWish(e.detail.id);
    this.refreshWish();
    wx.showToast({ title: added ? '已加入心愿单' : '已移出心愿单', icon: 'none' });
  },
  async onBag(e) {
    // 快速加购需选规格，跳详情
    wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.detail.id });
  },

  // 打开时草稿同步成已生效状态，避免上次选了没点应用的残留
  openFilter() {
    this.setData({ picked: Object.assign({}, this.data.applied), filterOpen: true });
  },
  closeFilter() { this.setData({ filterOpen: false }); },
  toggleExp(e) {
    const i = e.currentTarget.dataset.i;
    this.setData({ filterExp: this.data.filterExp === i ? -1 : i });
  },
  pickOpt(e) {
    const { g, v, multi } = e.currentTarget.dataset;
    const key = g + ':' + v;
    const picked = Object.assign({}, this.data.picked);
    const on = !!picked[key];
    // 单选组：先清掉同组其它选项
    if (!multi) Object.keys(picked).forEach((k) => { if (k.indexOf(g + ':') === 0) delete picked[k]; });
    if (on) delete picked[key]; else picked[key] = true;
    this.setData({ picked });
  },
  resetFilter() { this.setData({ picked: {} }); },
  applyFilter() {
    const applied = Object.assign({}, this.data.picked);
    this.setData({ applied, pickedCount: Object.keys(applied).length, filterOpen: false });
    this.fetch();
  }
});
