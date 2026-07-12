const app = getApp();
const api = require('../../utils/api.js');
const { toCard } = require('../../utils/mapper.js');

const FILTERS = [
  { t: '推荐系列', opts: ['SOLEIL', 'CALLA', 'RIVA', 'LUMEN'] },
  { t: '颜色', opts: ['黑色', '蓝色', '米白', '棕色', '拼色印花'] },
  { t: '尺码', opts: ['XS', 'S', 'M', 'L', 'XL'] },
  { t: '材质', opts: ['绢丝', '棉', '亚麻', '皮革'] },
  { t: '衣长', opts: ['短款', '中长款', '长款'] }
];

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
    filterExp: -1,
    filters: FILTERS,
    picked: {}
  },

  onLoad(opts) {
    const cat = opts.cat ? decodeURIComponent(opts.cat) : '';
    const seriesId = opts.series ? Number(opts.series) : 0;
    const title = opts.title ? decodeURIComponent(opts.title) : (cat || (seriesId ? '系列' : '全部商品'));
    this.setData({ cat, seriesId, title });
    this.fetch();
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

  async fetch() {
    try {
      const params = { page_size: 50, sort: this.data.sort };
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

  openFilter() { this.setData({ filterOpen: true }); },
  closeFilter() { this.setData({ filterOpen: false }); },
  toggleExp(e) {
    const i = e.currentTarget.dataset.i;
    this.setData({ filterExp: this.data.filterExp === i ? -1 : i });
  },
  pickOpt(e) {
    const { g, o } = e.currentTarget.dataset;
    const key = g + ':' + o;
    const picked = Object.assign({}, this.data.picked);
    if (picked[key]) delete picked[key]; else picked[key] = true;
    this.setData({ picked });
  },
  resetFilter() { this.setData({ picked: {} }); },
  applyFilter() {
    this.setData({ filterOpen: false });
    wx.showToast({ title: '筛选已应用', icon: 'none' });
  }
});
