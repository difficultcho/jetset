Page({
  data: { date: '' },
  onLoad() {
    const d = new Date();
    this.setData({ date: d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2) });
  },
  logoff() { wx.showToast({ title: '请联系在线客服办理', icon: 'none' }); }
});
