Page({
  data: { date: '' },
  onLoad() {
    const d = new Date();
    this.setData({ date: d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2) });
  },
  // 打开微信公众平台里配置的《用户隐私保护指引》，不在小程序里另写一份。
  openPrivacy() {
    if (!wx.openPrivacyContract) {
      wx.showToast({ title: '请升级微信后查看', icon: 'none' });
      return;
    }
    wx.openPrivacyContract({
      fail() { wx.showToast({ title: '隐私政策暂时无法打开', icon: 'none' }); }
    });
  },
  logoff() { wx.showToast({ title: '请联系在线客服办理', icon: 'none' }); }
});
