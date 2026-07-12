Component({
  data: {
    selected: 0,
    list: [
      { pagePath: '/pages/home/home', text: 'AURELLE', key: 'home' },
      { pagePath: '/pages/brand/brand', text: '关于品牌', key: 'brand' },
      { pagePath: '/pages/shop/shop', text: '商城', key: 'shop' },
      { pagePath: '/pages/me/me', text: '我的', key: 'me' },
      { pagePath: '/pages/stores/stores', text: '线下门店', key: 'stores' }
    ]
  },
  methods: {
    switchTab(e) {
      wx.switchTab({ url: e.currentTarget.dataset.path });
    },
    // 各 Tab 页 onShow 中调用，同步选中态
    refresh(selected) {
      this.setData({ selected });
    }
  }
});
