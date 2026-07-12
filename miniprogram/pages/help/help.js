const { helps } = require('../../utils/aurelle-data.js');
Page({
  data: { topics: helps.map((h) => ({ key: h.key, cn: h.cn, en: h.en })) },
  go(e) { wx.navigateTo({ url: '/pages/help-detail/help-detail?topic=' + e.currentTarget.dataset.k }); }
});
