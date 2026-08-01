// JET SET 子页导航栏：状态栏留白 + 返回箭头 + 居中标题 + 右侧 slot
Component({
  options: { multipleSlots: true },
  properties: {
    title: String,
    brand: Boolean,   // true 时标题渲染为品牌字标 JET SET
    border: { type: Boolean, value: true },
    back: { type: Boolean, value: true }
  },
  data: { sbh: 20 },
  attached() {
    this.setData({ sbh: getApp().refreshMetrics().sbh });
    // 本组件被 25 个子页共用，折叠屏展开/收起时在此统一响应，
    // 免得每个页面各写一份。直接调 refreshMetrics 而不读 globalData，
    // 是为了不依赖 app 与组件两个 resize 回调的执行顺序。
    this._onResize = () => this.setData({ sbh: getApp().refreshMetrics().sbh });
    if (wx.onWindowResize) wx.onWindowResize(this._onResize);
  },
  detached() {
    if (this._onResize && wx.offWindowResize) wx.offWindowResize(this._onResize);
  },
  methods: {
    onBack() {
      const pages = getCurrentPages();
      if (pages.length > 1) wx.navigateBack();
      else wx.switchTab({ url: '/pages/home/home' });
    }
  }
});
