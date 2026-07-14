const api = require('../../utils/api.js');
const { toBrand } = require('../../utils/mapper.js');
const { watchVideos, stopWatch } = require('../../utils/video-autoplay.js');

Page({
  data: { post: null },
  onUnload() { stopWatch(this); },
  async onLoad() {
    try {
      const p = await api.brandFirst('story');
      if (!p) return;
      const post = toBrand(p);
      this.setData({ post });
      const vids = post.body.map((b, i) => (b.kind === 'video' ? 'v' + i : null)).filter(Boolean);
      if (vids.length) wx.nextTick(() => watchVideos(this, vids));
    } catch (e) { /* 静默 */ }
  }
});
