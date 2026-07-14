// 视频进屏自动播：进入可视区自动播放（静音起播），离开自动暂停。
// ids 为页面内 <video> 元素 id 列表；重复调用会先清掉旧监听。
function watchVideos(page, ids) {
  stopWatch(page);
  page._vobs = ids.map((id) => {
    // 上下各收缩 100px：视频真正进入视野才起播，贴边不算
    const ob = page.createIntersectionObserver().relativeToViewport({ top: -100, bottom: -100 });
    ob.observe('#' + id, (res) => {
      const ctx = wx.createVideoContext(id, page);
      if (res.intersectionRatio > 0) ctx.play();
      else ctx.pause();
    });
    return ob;
  });
}

function stopWatch(page) {
  (page._vobs || []).forEach((o) => o.disconnect());
  page._vobs = [];
}

module.exports = { watchVideos, stopWatch };
