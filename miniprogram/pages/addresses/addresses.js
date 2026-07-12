const app = getApp();
const api = require('../../utils/api.js');
const { toAddress } = require('../../utils/mapper.js');

Page({
  data: { list: [], selectMode: false, showForm: false, form: { name: '', phone: '', full: '' }, editId: null },

  onLoad(opts) { this.setData({ selectMode: opts.select === '1' }); },
  onShow() { this.load(); },

  async load() {
    try {
      const list = await api.addresses();
      this.setData({ list: list.map(toAddress) });
    } catch (e) { /* 静默 */ }
  },

  // 微信收货地址（演示：注入一条）
  wxAddress() {
    wx.chooseAddress({
      success: async (a) => {
        try {
          await api.addressCreate({
            name: a.userName, phone: a.telNumber,
            region: a.provinceName + ' ' + a.cityName + ' ' + a.countyName,
            detail: a.detailInfo
          });
          this.load();
        } catch (e) { /* 静默 */ }
      },
      fail: () => {}
    });
  },

  pickAddr(e) {
    if (!this.data.selectMode) return;
    app.globalData.pickedAddrId = e.currentTarget.dataset.id;
    wx.navigateBack();
  },

  openNew() { this.setData({ showForm: true, editId: null, form: { name: '', phone: '', full: '' } }); },
  edit(e) {
    const a = this.data.list.find((x) => x.id === e.currentTarget.dataset.id);
    this.setData({ showForm: true, editId: a.id, form: { name: a.name, phone: a.phone, full: a.full } });
  },
  onInput(e) { this.setData({ ['form.' + e.currentTarget.dataset.k]: e.detail.value }); },
  cancelForm() { this.setData({ showForm: false }); },

  async save() {
    const f = this.data.form;
    if (!f.name || !f.phone || !f.full) return wx.showToast({ title: '请填写完整', icon: 'none' });
    const payload = { name: f.name, phone: f.phone, region: '', detail: f.full };
    try {
      if (this.data.editId) await api.addressUpdate(this.data.editId, payload);
      else await api.addressCreate(payload);
      this.setData({ showForm: false });
      this.load();
    } catch (e) { wx.showToast({ title: '保存失败', icon: 'none' }); }
  },

  async del(e) {
    const id = e.currentTarget.dataset.id;
    const r = await new Promise((res) => wx.showModal({ title: '删除地址', content: '确定删除该地址吗？', success: res }));
    if (!r.confirm) return;
    try { await api.addressDelete(id); this.load(); } catch (e2) { /* 静默 */ }
  },

  async setDefault(e) {
    try { await api.addressSetDefault(e.currentTarget.dataset.id); this.load(); } catch (e2) { /* 静默 */ }
  }
});
