const api = require('../../utils/api.js');
const { toCard, toBrand } = require('../../utils/mapper.js');
const { watchVideos, stopWatch } = require('../../utils/video-autoplay.js');

Page({
  data: { post: null, prods: [], seriesEn: '' },
  onUnload() { stopWatch(this); },
  async onLoad() {
    try {
      const p = await api.brandFirst('campaign');
      if (!p) return;
      const post = toBrand(p);
      this.setData({ post });
      const vids = post.body.map((b, i) => (b.kind === 'video' ? 'v' + i : null)).filter(Boolean);
      if (vids.length) wx.nextTick(() => watchVideos(this, vids));
      // 关联了系列 → 尾部同系列单品导购条
      if (post.series) {
        const page = await api.products({ series: post.series.id, page_size: 6 });
        this.setData({
          prods: page.items.map(toCard),
          seriesEn: post.series.en || post.series.name
        });
      }
    } catch (e) { /* 静默 */ }
  },
  goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.currentTarget.dataset.id }); }
});
