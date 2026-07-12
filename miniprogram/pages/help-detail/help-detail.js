const { helps } = require('../../utils/aurelle-data.js');
Page({
  data: { title: '帮助中心', qas: [], isSize: false },
  onLoad(opts) {
    const h = helps.find((x) => x.key === opts.topic) || helps[0];
    this.setData({ title: '帮助中心 - ' + h.cn, qas: h.qas, isSize: h.key === 'size' });
  },
  goSizeGuide() { wx.navigateTo({ url: '/pages/size-guide/size-guide' }); }
});
