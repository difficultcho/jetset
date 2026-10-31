const api = require('../../utils/api.js');
const { toStore } = require('../../utils/mapper.js');
const { paintQr, seedFrom } = require('../../utils/fake-qr.js');

Page({
  data: { stores: [], idx: 0 },
  async onLoad() {
    try {
      const stores = await api.stores();
      this.setData({ stores: stores.map(toStore) }, () => this.paint());
    } catch (e) { /* 静默 */ }
  },
  next() {
    if (!this.data.stores.length) return;
    this.setData({ idx: (this.data.idx + 1) % this.data.stores.length }, () => this.paint());
  },
  // 门店已上传导购码时用图片。否则在画布上按门店编号画一张。
  paint(tryN) {
    const store = this.data.stores[this.data.idx];
    const seq = (this._paintSeq || 0) + 1;
    this._paintSeq = seq;
    if (!store || store.qr) return;
    const n = tryN || 0;
    wx.nextTick(() => {
      if (this._paintSeq !== seq) return;
      this.createSelectorQuery().select('#guide-qr').fields({ node: true, size: true }).exec((res) => {
        if (this._paintSeq !== seq) return;
        const box = res && res[0];
        if (!box || !box.node || !box.width) {
          if (n < 5) setTimeout(() => { if (this._paintSeq === seq) this.paint(n + 1); }, 60);
          return;
        }
        const canvas = box.node;
        const ctx = canvas.getContext('2d');
        const dpr = (wx.getWindowInfo && wx.getWindowInfo().pixelRatio) || 2;
        canvas.width = box.width * dpr;
        canvas.height = box.height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        paintQr(ctx, box.width, seedFrom(store.id));
      });
    });
  }
});
