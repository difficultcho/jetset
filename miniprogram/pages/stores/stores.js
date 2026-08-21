const app = getApp();
const api = require('../../utils/api.js');
const { toStore } = require('../../utils/mapper.js');

Page({
  // heroA/heroB：两个入口的封面图，取自门店实拍；取不到则回落到 wxml 里的条纹占位
  data: { sbh: 20, heroA: '', heroB: '' },

  onLoad() { this.setData({ sbh: app.refreshMetrics().sbh }); },
  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(4);
    app.refreshCartCount();
    // tab 页 onLoad 只跑一次；门店图在后台换了要能刷出来，取数放 onShow
    this.fetchHeroes();
  },

  // 门店没有「门头/内景」的字段区分，所以按门店顺序把所有图拉平，取前两张。
  // 这样两个入口一定是不同的图；只有一张图时第二个入口自然回落到占位。
  async fetchHeroes() {
    try {
      const imgs = [];
      for (const s of (await api.stores()) || []) {
        for (const u of toStore(s).images) if (u) imgs.push(u);
        if (imgs.length >= 2) break;
      }
      this.setData({ heroA: imgs[0] || '', heroB: imgs[1] || '' });
    } catch (e) { /* 静默：保持占位图，不影响两个入口可点 */ }
  },

  // 折叠屏展开/收起、分屏会改变窗口尺寸，状态栏高度需重算
  onResize() { this.setData({ sbh: app.refreshMetrics().sbh }); },
  goNearby() { wx.navigateTo({ url: '/pages/nearby/nearby' }); },
  goIntro() { wx.navigateTo({ url: '/pages/store-intro/store-intro' }); }
});
