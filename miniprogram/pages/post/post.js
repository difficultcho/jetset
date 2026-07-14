const api = require('../../utils/api.js');
const { toCard, toBrand } = require('../../utils/mapper.js');
const { watchVideos, stopWatch } = require('../../utils/video-autoplay.js');

// 通用品牌帖详情：活动项目（含子项目）/系列专题/任意 brand_post
Page({
  data: { post: null, prods: [], seriesEn: '' },
  onUnload() { stopWatch(this); },
  async onLoad(opts) {
    try {
      const p = await api.brandPost(opts.id);
      const post = toBrand(p);
      this.setData({ post });
      const vids = post.body.map((b, i) => (b.kind === 'video' ? 'v' + i : null)).filter(Boolean);
      if (vids.length) wx.nextTick(() => watchVideos(this, vids));
      if (post.series) {
        const page = await api.products({ series: post.series.id, page_size: 6 });
        this.setData({
          prods: page.items.map(toCard),
          seriesEn: post.series.en || post.series.name
        });
      }
    } catch (e) {
      wx.showToast({ title: '内容加载失败', icon: 'none' });
    }
  },
  goSub(e) { wx.navigateTo({ url: '/pages/post/post?id=' + e.currentTarget.dataset.id }); },
  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.currentTarget.dataset.id }); }
});
