// 类型化跳转：后端已把链接解析成导航参数，这里只负责拼 url。
// 页面块（page-blocks）与商城（shop）共用，避免两处各写一份跳转规则。

// navigateTo 失败默认是静默的（页面没在 app.json 注册、页面栈超 10 层都会失败），
// 表现成"点了没反应"，极难排查。统一在这里兜底报错。
function go2(url) {
  wx.navigateTo({
    url,
    fail(err) {
      console.error('[nav] 跳转失败：' + url, err);
      wx.showToast({ title: '页面打不开', icon: 'none' });
    }
  });
}

function goList(f) {
  const q = [];
  if (f.cat) q.push('cat=' + encodeURIComponent(f.cat));
  if (f.series) q.push('series=' + f.series);
  q.push('title=' + encodeURIComponent(f.title || '全部商品'));
  go2('/pages/list/list?' + q.join('&'));
}

function go(link) {
  if (!link) return;
  if (link.kind === 'page') {
    // 后端解析链接时已带出目标页标题，顺手传过去，避免内容页「空白→填上」的跳变
    return go2('/pages/page/page?key=' + link.key
               + '&title=' + encodeURIComponent(link.title || ''));
  }
  if (link.kind === 'pdp') return go2('/pages/pdp/pdp?id=' + link.spu_id);
  if (link.kind === 'list') return goList(link);
}

module.exports = { go, goList };
