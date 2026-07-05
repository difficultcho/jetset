const api = require('../../utils/api.js');
const { toAddress } = require('../../utils/mapper.js');
const { toastError } = require('../../utils/request.js');

Page({
  data: {
    list: [],
    showF: false,
    form: { name: '', phone: '', address: '' },
    editId: null
  },

  onShow() {
    this.load();
  },

  async load() {
    try {
      const list = await api.addresses();
      this.setData({ list: list.map(toAddress) });
    } catch (e) {
      toastError(e);
    }
  },

  openF() {
    this.setData({ showF: true, editId: null, form: { name: '', phone: '', address: '' } });
  },

  edit(e) {
    const a = this.data.list.find((x) => x.id === e.currentTarget.dataset.id);
    if (!a) return;
    this.setData({
      showF: true,
      editId: a.id,
      form: { name: a.name, phone: a.phone, address: a.address }
    });
  },

  cancel() {
    this.setData({ showF: false });
  },

  onInput(e) {
    this.setData({ ['form.' + e.currentTarget.dataset.k]: e.detail.value });
  },

  async save() {
    const f = this.data.form;
    // 姓名/手机/地址全部非空才允许保存
    if (!f.name || !f.phone || !f.address) {
      wx.showToast({ title: '请填写完整信息', icon: 'none' });
      return;
    }
    const payload = { name: f.name, phone: f.phone, region: '', detail: f.address };
    try {
      if (this.data.editId) {
        await api.addressUpdate(this.data.editId, payload);
      } else {
        await api.addressCreate(payload); // 服务端自动置为默认（列表顶部）
      }
      this.setData({ showF: false });
      await this.load();
    } catch (e) {
      toastError(e);
    }
  }
});
