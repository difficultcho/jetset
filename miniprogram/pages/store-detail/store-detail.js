const api = require('../../utils/api.js');
const { toStore } = require('../../utils/mapper.js');

Page({
  data: { store: null },
  async onLoad(opts) {
    try {
      const s = await api.storeDetail(opts.id);
      this.setData({ store: toStore(s) });
    } catch (e) { wx.showToast({ title: '门店加载失败', icon: 'none' }); }
  },
  call() { if (this.data.store) wx.makePhoneCall({ phoneNumber: this.data.store.tel }); }
});
