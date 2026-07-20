const app = getApp();
const api = require('../../utils/api.js');
const { toCard, fullImg } = require('../../utils/mapper.js');
const { watchVideos } = require('../../utils/video-autoplay.js');

Page({
  data: { sbh: 20, heroH: 600, heroImg: '', bagCount: 0, prods: [], prodIdx: 0, scrollTop: 0,
          campTitle: '', campCover: '', catBlocks: [], seriesLabel: '', hsId: 0, hsEn: '' },

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
      const [feat, home, series, camp, tree] = await Promise.all([
        api.products({ featured: 1, page_size: 10 }),
        api.home(), api.series(), api.brandFirst('campaign'), api.categories()
      ]);

      // 走马灯取材：精选商品优先（勾几个轮几帧）；无精选回退默认前 3
      if (feat.items.length) {
        this.setData({ prods: feat.items.map(toCard) });
      } else {
        const page = await api.products({ page_size: 6 });
        this.setData({ prods: page.items.slice(0, 3).map(toCard) });
      }

      // 首页首图：后台「首页首图」排序最前的启用项（无图时保留占位帧）
      const first = (home.banners || [])[0];
      if (first && first.image) this.setData({ heroImg: fullImg(first.image) });

      // 当季主推系列 = 排序最前的启用系列（首图点击 + 左下 link 同一目标，后台调排序即切换）
      const hs = series[0];
      if (hs) {
        this.setData({
          hsId: hs.id, hsEn: hs.en,
          seriesLabel: '探索 ' + [hs.en, hs.name].filter(Boolean).join(' ')
        });
      }

      // 视频位：后台「首页首图」页配置的系列 → 播该系列内容帖的第一个视频，链接指向该系列页
      const v = home.video;
      if (v && v.src) {
        this.setData({ homeVideo: {
          src: fullImg(v.src), poster: v.poster ? fullImg(v.poster) : '', postId: v.post_id,
          label: '探索 ' + [v.series_en, v.series_name].filter(Boolean).join(' ')
        } });
        wx.nextTick(() => watchVideos(this, ['vhome']));
      }

      // 大片首帖：视频位占位跳转文案 + 大片内容块封面
      if (camp) {
        this.setData({ campTitle: camp.title || '', campCover: camp.cover ? fullImg(camp.cover) : '' });
      }

      // 品类导览块：前两个叶子品类，各取该品类第一个商品图
      const leaves = [];
      tree.forEach((t) => (t.children.length ? t.children : [t]).forEach((c) => leaves.push(c.name)));
      const two = leaves.slice(0, 2);
      const BGS = [
        'repeating-linear-gradient(135deg,#ecd9c2 0 32rpx,#e6cfb2 32rpx 64rpx)',
        'repeating-linear-gradient(135deg,#d9d4cc 0 32rpx,#cfc8bd 32rpx 64rpx)'
      ];
      const thumbs = await Promise.all(two.map((n) => api.products({ cat: n, page_size: 1 }).catch(() => null)));
      this.setData({
        catBlocks: two.map((n, i) => ({
          name: n, bg: BGS[i % 2],
          img: (thumbs[i] && thumbs[i].items[0] && thumbs[i].items[0].image)
            ? fullImg(thumbs[i].items[0].image) : ''
        }))
      });
    } catch (e) {
      console.error('[home] 取数失败：', e && e.message);
      wx.showToast({ title: '加载失败：' + ((e && e.message) || '网络错误'), icon: 'none', duration: 3000 });
    }
  },

  goCat(e) {
    const name = e.currentTarget.dataset.name;
    wx.navigateTo({ url: '/pages/list/list?cat=' + encodeURIComponent(name) + '&title=' + encodeURIComponent(name) });
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
  goSeries() {
    if (!this.data.hsId) return this.goList();
    wx.navigateTo({ url: '/pages/list/list?series=' + this.data.hsId + '&title=' + encodeURIComponent(this.data.hsEn || '系列') });
  },
  goCampaign() { wx.navigateTo({ url: '/pages/campaign/campaign' }); },
  goVideoPost() {
    const hv = this.data.homeVideo;
    if (hv && hv.postId) wx.navigateTo({ url: '/pages/post/post?id=' + hv.postId });
    else this.goCampaign();
  },
  goList() { wx.navigateTo({ url: '/pages/list/list' }); },
  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.currentTarget.dataset.id }); },
  goSearch() { wx.navigateTo({ url: '/pages/search/search' }); }
});
