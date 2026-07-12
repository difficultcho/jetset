const app = getApp();

Page({
  data: {
    sbh: 20,
    playing: false,
    blocks: [
      { c1: '#dcdfe0', c2: '#d0d4d6', ph: 'video · 林间白裙', t: 'HIGH SUMMER 2026 影片', video: true, go: 'campaign' },
      { c1: '#dde3ea', c2: '#d3dbe4', ph: 'editorial · A.PROJECTS', t: 'A.PROJECTS 创作企划', go: 'projects' },
      { c1: '#e8dcc8', c2: '#e0d2b9', ph: 'moments · 品牌活动', t: 'A.MOMENTS 精彩瞬间', time: true, go: 'moments' }
    ],
    blocks2: [
      { c1: '#e5ddce', c2: '#ddd3c0', ph: 'story · 品牌故事', t: '品牌故事 THE STORY', go: 'story' },
      { c1: '#e0dbd2', c2: '#d8d2c6', ph: 'boutique · 走进精品店', t: '走进精品店 BOUTIQUE', go: 'storeIntro' }
    ]
  },

  onLoad() { this.setData({ sbh: app.globalData.statusBarHeight }); },
  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(1);
    app.refreshCartCount();
  },

  togglePlay() { this.setData({ playing: !this.data.playing }); },
  go(e) {
    const go = e.currentTarget.dataset.go;
    const map = { campaign: '/pages/campaign/campaign', projects: '/pages/projects/projects', moments: '/pages/moments/moments', story: '/pages/story/story', storeIntro: '/pages/store-intro/store-intro' };
    wx.navigateTo({ url: map[go] });
  }
});
