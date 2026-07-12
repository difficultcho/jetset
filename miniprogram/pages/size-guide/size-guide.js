const { sizeApparel, sizeBody, sizeShoe } = require('../../utils/aurelle-data.js');
Page({
  data: {
    tables: [
      { title: '服饰尺码对照', t: sizeApparel },
      { title: '身体围度 (cm)', t: sizeBody },
      { title: '鞋履尺码', t: sizeShoe }
    ]
  }
});
