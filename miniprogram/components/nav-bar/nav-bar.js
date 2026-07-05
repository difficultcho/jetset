// 自定义导航栏：用于 navigationStyle: custom 的页面（状态栏留白 + 44px 标题栏）
Component({
  options: { multipleSlots: true },
  properties: {
    title: String,
    light: Boolean,       // 浅色文字（深色/图片背景上使用）
    transparent: Boolean, // 透明背景
    border: { type: Boolean, value: true },
    back: Boolean
  },
  data: { sbh: 20 },
  attached() {
    this.setData({ sbh: getApp().globalData.statusBarHeight });
  },
  methods: {
    onBack() {
      wx.navigateBack();
    }
  }
});
