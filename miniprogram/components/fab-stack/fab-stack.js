// 右下悬浮按钮栈：客服 / 购物袋(带角标) / 回到顶部
Component({
  properties: {
    showService: { type: Boolean, value: false },
    showBag: { type: Boolean, value: false },
    showTop: { type: Boolean, value: false },
    bagSize: { type: Number, value: 104 },  // 设计稿 52px；pdp 用 88（44px）
    bottom: { type: Number, value: 104 },
    aboveTab: { type: Boolean, value: false } // Tab 页：自动抬到 tabBar 之上（含安全区）
  },
  data: { cnt: 0 },
  attached() {
    this.setData({ cnt: getApp().globalData.cartCount });
  },
  methods: {
    refresh() {
      this.setData({ cnt: getApp().globalData.cartCount });
    },
    goBag() {
      wx.navigateTo({ url: '/pages/bag/bag' });
    },
    toTop() {
      this.triggerEvent('totop');
    }
  }
});
