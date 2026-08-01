const app = getApp();

Page({
  data: { sbh: 20 },
  onLoad() { this.setData({ sbh: app.refreshMetrics().sbh }); },
  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(4);
    app.refreshCartCount();
  },

  // 折叠屏展开/收起、分屏会改变窗口尺寸，状态栏高度需重算
  onResize() { this.setData({ sbh: app.refreshMetrics().sbh }); },
  goNearby() { wx.navigateTo({ url: '/pages/nearby/nearby' }); },
  goIntro() { wx.navigateTo({ url: '/pages/store-intro/store-intro' }); }
});
