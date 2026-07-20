// 配置化页面块渲染器：接收已解析的块序列，负责跳转 / 走马灯圆点 / 视频进屏自动播。
Component({
  properties: {
    blocks: { type: Array, value: [], observer(v) { this._watchVideos(v); } },
    heroH: { type: Number, value: 0 }   // 撑满首屏图的高度（页面按自身头部算好传入）
  },

  data: { dots: {} },   // 走马灯块索引 → 当前圆点

  lifetimes: {
    detached() { this._disconnect(); }
  },

  methods: {
    _disconnect() { (this._obs || []).forEach((o) => o.disconnect()); this._obs = []; },

    // 视频块进入视野自动静音播放，离开暂停
    _watchVideos(blocks) {
      this._disconnect();
      (blocks || []).forEach((b, i) => {
        if (b.kind !== 'video') return;
        const ob = this.createIntersectionObserver().relativeToViewport({ top: -100, bottom: -100 });
        ob.observe('#vb' + i, (res) => {
          const ctx = wx.createVideoContext('vb' + i, this);
          if (res.intersectionRatio > 0) ctx.play(); else ctx.pause();
        });
        (this._obs || (this._obs = [])).push(ob);
      });
    },

    // 页面 onHide 时调用，暂停全部视频
    pauseVideos() {
      (this.data.blocks || []).forEach((b, i) => {
        if (b.kind === 'video') wx.createVideoContext('vb' + i, this).pause();
      });
    },

    onCarousel(e) { this.setData({ ['dots.' + e.currentTarget.dataset.i]: e.detail.current }); },

    goPdp(e) { wx.navigateTo({ url: '/pages/pdp/pdp?id=' + e.currentTarget.dataset.id }); },

    // 类型化跳转（后端已把链接解析成导航参数）；链接行按左右取各自 link
    goLink(e) {
      const { i, side } = e.currentTarget.dataset;
      const b = this.data.blocks[i];
      let l = b && b.link;
      if (b && b.kind === 'linkrow') l = side === 'right' ? (b.right && b.right.link) : (b.left && b.left.link);
      if (!l) return;
      if (l.kind === 'page') return wx.navigateTo({ url: '/pages/page/page?key=' + l.key });
      if (l.kind === 'pdp') return wx.navigateTo({ url: '/pages/pdp/pdp?id=' + l.spu_id });
      if (l.kind === 'list') {
        let url = '/pages/list/list?';
        if (l.cat) url += 'cat=' + encodeURIComponent(l.cat) + '&';
        if (l.series) url += 'series=' + l.series + '&';
        wx.navigateTo({ url: url + 'title=' + encodeURIComponent(l.title || '全部商品') });
      }
    }
  }
});
