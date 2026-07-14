const app = getApp();
const api = require('../../utils/api.js');
const { fullImg } = require('../../utils/mapper.js');

// 「关于品牌」tab：固定四区块（故事/门店/系列/活动），内容全部后台可配
Page({
  data: {
    sbh: 20,
    covers: { story: '', store: '', campaign: '', project: '', moment: '' },
    campTitle: 'CAMPAIGN',
    seriesPosts: []
  },

  onLoad() {
    this.setData({ sbh: app.globalData.statusBarHeight });
    this.fetch();
  },

  async fetch() {
    try {
      const [story, camp, moment, projects, seriesPosts, stores] = await Promise.all([
        api.brandFirst('story'), api.brandFirst('campaign'), api.brandFirst('moment'),
        api.brandPosts('project'), api.seriesPosts(), api.stores()
      ]);
      this.setData({
        covers: {
          story: story && story.cover ? fullImg(story.cover) : '',
          store: stores[0] && stores[0].images && stores[0].images[0] ? fullImg(stores[0].images[0]) : '',
          campaign: camp && camp.cover ? fullImg(camp.cover) : '',
          project: projects[0] && projects[0].cover ? fullImg(projects[0].cover) : '',
          moment: moment && moment.cover ? fullImg(moment.cover) : ''
        },
        campTitle: (camp && camp.title) || 'CAMPAIGN',
        seriesPosts: seriesPosts.map((p) => ({
          id: p.id, title: p.title, subtitle: p.subtitle,
          cover: fullImg(p.cover), tint: p.cover_tint || '#e8dcc8'
        }))
      });
    } catch (e) { /* 静默，保留占位 */ }
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(1);
    app.refreshCartCount();
  },

  go(e) {
    const go = e.currentTarget.dataset.go;
    const map = { campaign: '/pages/campaign/campaign', projects: '/pages/projects/projects', moments: '/pages/moments/moments', story: '/pages/story/story', storeIntro: '/pages/store-intro/store-intro' };
    wx.navigateTo({ url: map[go] });
  },
  goPost(e) { wx.navigateTo({ url: '/pages/post/post?id=' + e.currentTarget.dataset.id }); }
});
