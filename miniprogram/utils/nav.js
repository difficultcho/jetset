// 类型化跳转：后端已把链接解析成导航参数，这里只负责拼 url。
// 页面块（page-blocks）与商城（shop）共用，避免两处各写一份跳转规则。

function goList(f) {
  const q = [];
  if (f.cat) q.push('cat=' + encodeURIComponent(f.cat));
  if (f.series) q.push('series=' + f.series);
  q.push('title=' + encodeURIComponent(f.title || '全部商品'));
  wx.navigateTo({ url: '/pages/list/list?' + q.join('&') });
}

function go(link) {
  if (!link) return;
  if (link.kind === 'page') return wx.navigateTo({ url: '/pages/page/page?key=' + link.key });
  if (link.kind === 'pdp') return wx.navigateTo({ url: '/pages/pdp/pdp?id=' + link.spu_id });
  if (link.kind === 'list') return goList(link);
}

module.exports = { go, goList };
