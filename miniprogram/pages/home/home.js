const app = getApp();
const api = require('../../utils/api.js');
const { toCard, fullImg } = require('../../utils/mapper.js');
const { watchVideos } = require('../../utils/video-autoplay.js');

Page({
  data: { sbh: 20, heroH: 600, heroImg: '', bagCount: 0, prods: [], prodIdx: 0, scrollTop: 0 },

  onLoad() {
    const sbh = app.globalData.statusBarHeight;
    // 首图撑满首屏：窗口高 −（状态栏 + 88rpx 头部）
    const win = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    const heroH = win.windowHeight - sbh - Math.round((win.windowWidth * 88) / 750);
    this.setData({ sbh, heroH });
    this.fetch();
  },

  async fetch() {
    try {
      const page = await api.products({ page_size: 6 });
      this.setData({ prods: page.items.slice(0, 3).map(toCard) });
      // 首页首图：后台「首页首图」排序最前的启用项（无图时保留占位帧）
      const home = await api.home();
      const first = (home.banners || [])[0];
      if (first && first.image) this.setData({ heroImg: fullImg(first.image) });
      // STARS 系列 id（供"探索 STARS 星星系列"跳转）
      const series = await api.series();
      const hs = series.find((s) => s.en === 'STARS') || series[0];
      if (hs) this.setData({ hsId: hs.id, hsEn: hs.en });
      // 首页视频位：广告大片首帖的第一个视频块（无则维持占位）
      const camp = await api.brandFirst('campaign');
      const v = camp && (camp.body || []).find((b) => b.kind === 'video' && b.src);
      if (v) {
        this.setData({ homeVideo: { src: fullImg(v.src), poster: v.poster ? fullImg(v.poster) : '' } });
        wx.nextTick(() => watchVideos(this, ['vhome']));
      }
    } catch (e) {
      console.error('[home] 取商品失败：', e && e.message);
      wx.showToast({ title: '商品加载失败：' + ((e && e.message) || '网络错误'), icon: 'none', duration: 3000 });
    }
  },

  onHide() {
    // 切走 tab 时暂停首页视频（回来后滑动进屏会自动续播）
    if (this.data.homeVideo) wx.createVideoContext('vhome', this).pause();
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(0);
    app.refreshCartCount().then((c) => this.setData({ bagCount: c }));
    // 首次因登录时序失败时，回到首页补取一次
    if (!this.data.prods.length) this.fetch();
  },

  // swiper 切换（含手势/自动播放）时同步自定义圆点（单向，不回写 current）
  prodChange(e) { this.setData({ prodIdx: e.detail.current }); },
  scrollToTop() { this.setData({ scrollTop: this.data.scrollTop === 0 ? 1 : 0 }); },

  goBag() { wx.navigateTo({ url: '/pages/bag/bag' }); },
  goCampaign() { wx.navigateTo({ url: '/pages/campaign/campaign' }); },
  goSeries() {
    const id = this.data.hsId || 1;
    wx.navigateTo({ url: '/pages/list/list?series=' + id + '&title=' + encodeURIComponent(this.data.hsEn) });
  },
  goList() { wx.navigateTo({ url: '/pages/list/list' }); },
  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.currentTarget.dataset.id }); },
  goSearch() { wx.navigateTo({ url: '/pages/search/search' }); }
});
