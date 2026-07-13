const app = getApp();
const api = require('../../utils/api.js');
const { toCard, fullImg } = require('../../utils/mapper.js');

// 与设计稿一致的 Hero 三帧（后台未配置轮播图时的占位）
const HERO = [
  { k: 'h0', c1: '#ecd9cb', c2: '#e5cebc', label: 'campaign · 崖畔印花套装' },
  { k: 'h1', c1: '#e9dfce', c2: '#e2d5bf', label: 'campaign · 金纱帘光影' },
  { k: 'h2', c1: '#dfe5e9', c2: '#d5dde3', label: 'campaign · 泳池假日' }
];

Page({
  data: { sbh: 20, hero: HERO, heroIdx: 0, prods: [], prodIdx: 0, scrollTop: 0 },

  onLoad() {
    this.setData({ sbh: app.globalData.statusBarHeight });
    this.fetch();
  },

  async fetch() {
    try {
      const page = await api.products({ page_size: 6 });
      this.setData({ prods: page.items.slice(0, 3).map(toCard) });
      // 后台配置的 Hero 轮播（有图用图，无图用占位帧）
      const home = await api.home();
      const banners = (home.banners || []).map((b, i) => ({
        k: 'b' + i, img: fullImg(b.image),
        label: b.title || '', c1: '#e9dfce', c2: '#e2d5bf'
      }));
      if (banners.length) this.setData({ hero: banners, heroIdx: 0 });
      // STARS 系列 id（供"探索 STARS 星星系列"跳转）
      const series = await api.series();
      const hs = series.find((s) => s.en === 'STARS') || series[0];
      if (hs) this.setData({ hsId: hs.id, hsEn: hs.en });
    } catch (e) {
      console.error('[home] 取商品失败：', e && e.message);
      wx.showToast({ title: '商品加载失败：' + ((e && e.message) || '网络错误'), icon: 'none', duration: 3000 });
    }
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(0);
    app.refreshCartCount();
    // 首次因登录时序失败时，回到首页补取一次
    if (!this.data.prods.length) this.fetch();
  },

  // swiper 切换（含手势/自动播放）时同步自定义圆点
  heroChange(e) { this.setData({ heroIdx: e.detail.current }); },
  prodChange(e) { this.setData({ prodIdx: e.detail.current }); },
  setHero(e) { this.setData({ heroIdx: e.currentTarget.dataset.i }); },
  scrollToTop() { this.setData({ scrollTop: this.data.scrollTop === 0 ? 1 : 0 }); },

  goCampaign() { wx.navigateTo({ url: '/pages/campaign/campaign' }); },
  goSeries() {
    const id = this.data.hsId || 1;
    wx.navigateTo({ url: '/pages/list/list?series=' + id + '&title=' + encodeURIComponent(this.data.hsEn) });
  },
  goList() { wx.navigateTo({ url: '/pages/list/list' }); },
  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.currentTarget.dataset.id }); },
  goSearch() { wx.navigateTo({ url: '/pages/list/list' }); }
});
