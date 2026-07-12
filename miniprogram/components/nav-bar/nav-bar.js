// AURELLE 子页导航栏：状态栏留白 + 返回箭头 + 居中标题 + 右侧 slot
Component({
  options: { multipleSlots: true },
  properties: {
    title: String,
    brand: Boolean,   // true 时标题渲染为品牌字标 AURELLE
    border: { type: Boolean, value: true },
    back: { type: Boolean, value: true }
  },
  data: { sbh: 20 },
  attached() {
    this.setData({ sbh: getApp().globalData.statusBarHeight });
  },
  methods: {
    onBack() {
      const pages = getCurrentPages();
      if (pages.length > 1) wx.navigateBack();
      else wx.switchTab({ url: '/pages/home/home' });
    }
  }
});
