const app = getApp();
const api = require('../../utils/api.js');
const { toProd, toDetail } = require('../../utils/mapper.js');
const { toastError } = require('../../utils/request.js');

const SORT_KEYS = ['default', 'sales', 'price_asc', 'newest'];

Page({
  data: {
    cats: [],
    cat: '',
    q: '',
    sorts: ['综合', '销量', '价格', '上新'],
    sortIdx: 0,
    list: [],
    quickAdd: null
  },

  async onLoad() {
    try {
      const cats = await api.categories();
      const names = cats.map((c) => c.name);
      this.setData({ cats: names, cat: names[0] || '' });
      await this.fetchList();
    } catch (e) {
      toastError(e);
    }
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(1);
    app.refreshCartCount().then(() => {
      if (typeof this.getTabBar === 'function') this.getTabBar().refresh(1);
    });
  },

  async fetchList() {
    const { cat, q, sortIdx } = this.data;
    try {
      const page = await api.products({ cat, q, sort: SORT_KEYS[sortIdx], page_size: 50 });
      this.setData({ list: page.items.map(toProd) });
    } catch (e) {
      toastError(e);
    }
  },

  onSearch(e) {
    this.setData({ q: e.detail.value });
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.fetchList(), 300);
  },

  pickCat(e) {
    this.setData({ cat: e.currentTarget.dataset.c });
    this.fetchList();
  },

  pickSort(e) {
    this.setData({ sortIdx: e.currentTarget.dataset.i });
    this.fetchList();
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/product/product?id=' + e.currentTarget.dataset.id });
  },

  // 点击列表项的圆形购物车图标：拉详情（含 SKU）后弹配置选择弹窗
  async openQuick(e) {
    try {
      const d = await api.productDetail(e.currentTarget.dataset.id);
      this.setData({ quickAdd: toDetail(d) });
    } catch (err) {
      toastError(err);
    }
  },

  closeQuick() {
    this.setData({ quickAdd: null });
  },

  async confirmQuick(e) {
    try {
      await api.cartAdd(e.detail.skuId, e.detail.qty);
      this.setData({ quickAdd: null });
      await app.refreshCartCount();
      if (typeof this.getTabBar === 'function') this.getTabBar().refresh(1);
      wx.showToast({ title: '已加入购物车', icon: 'success' });
    } catch (err) {
      toastError(err);
    }
  }
});
