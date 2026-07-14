const api = require('../../utils/api.js');
const { toCard, toBrand } = require('../../utils/mapper.js');

// 通用品牌帖详情：活动项目（含子项目）/系列专题/任意 brand_post
Page({
  data: { post: null, prods: [], seriesEn: '' },
  async onLoad(opts) {
    try {
      const p = await api.brandPost(opts.id);
      const post = toBrand(p);
      this.setData({ post });
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
