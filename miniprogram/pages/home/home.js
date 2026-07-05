const app = getApp();
const api = require('../../utils/api.js');
const { toProd } = require('../../utils/mapper.js');
const { toastError } = require('../../utils/request.js');

Page({
  data: {
    sbh: 20,
    slide: 0,
    slides: [],
    hot: [],
    featured: null,
    grid: []
  },

  onLoad() {
    this.setData({ sbh: app.globalData.statusBarHeight });
    this.fetch();
  },

  async fetch() {
    try {
      const d = await api.home();
      this.setData({
        slides: d.banners.map((b) => ({ title: b.title, sub: b.sub_title })),
        hot: d.hot.map(toProd),
        featured: d.featured ? toProd(d.featured) : null,
        grid: d.grid.map(toProd)
      });
    } catch (e) {
      toastError(e);
    }
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(0);
    app.refreshCartCount().then(() => {
      if (typeof this.getTabBar === 'function') this.getTabBar().refresh(0);
    });
    this.timer = setInterval(() => {
      const n = this.data.slides.length;
      if (n) this.setData({ slide: (this.data.slide + 1) % n });
    }, 3500);
  },

  onHide() {
    clearInterval(this.timer);
  },

  onUnload() {
    clearInterval(this.timer);
  },

  setSlide(e) {
    this.setData({ slide: e.currentTarget.dataset.i });
  },

  goShop() {
    wx.switchTab({ url: '/pages/shop/shop' });
  }
});
