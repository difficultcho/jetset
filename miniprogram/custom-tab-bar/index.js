Component({
  data: {
    selected: 0,
    cnt: 0,
    list: [
      { pagePath: '/pages/home/home', text: '首页', key: 'home' },
      { pagePath: '/pages/shop/shop', text: '商品', key: 'shop' },
      { pagePath: '/pages/cart/cart', text: '购物车', key: 'cart' },
      { pagePath: '/pages/wholesale/wholesale', text: '批发', key: 'wholesale' },
      { pagePath: '/pages/mine/mine', text: '我的', key: 'mine' }
    ]
  },
  methods: {
    switchTab(e) {
      wx.switchTab({ url: e.currentTarget.dataset.path });
    },
    // 各 Tab 页 onShow 中调用，同步选中态与购物车角标
    refresh(selected) {
      this.setData({ selected, cnt: getApp().cartCount() });
    }
  }
});
