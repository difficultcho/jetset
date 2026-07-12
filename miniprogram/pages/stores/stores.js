const app = getApp();

Page({
  data: { sbh: 20 },
  onLoad() { this.setData({ sbh: app.globalData.statusBarHeight }); },
  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(4);
    app.refreshCartCount();
  },
  goNearby() { wx.navigateTo({ url: '/pages/nearby/nearby' }); },
  goIntro() { wx.navigateTo({ url: '/pages/store-intro/store-intro' }); }
});
