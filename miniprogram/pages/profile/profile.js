const api = require('../../utils/api.js');
const { upload, toastError } = require('../../utils/request.js');
const { API_BASE } = require('../../utils/config.js');

Page({
  data: { user: null },

  async onLoad() {
    try {
      const u = await api.me();
      this.setData({
        user: {
          name: u.name,
          avatar: u.avatar,
          phone: u.phone || '未绑定',
          gender: u.gender,
          birthday: u.birthday,
          region: u.region,
          reco: u.reco_enabled
        }
      });
      this.dirty = {};
    } catch (e) {
      toastError(e);
    }
  },

  // 设计稿：返回时自动保存修改
  onUnload() {
    if (this.dirty && Object.keys(this.dirty).length) {
      api.updateMe(this.dirty).catch(() => {});
    }
  },

  _set(field, value, apiField) {
    this.setData({ ['user.' + field]: value });
    this.dirty[apiField || field] = value;
  },

  editName() {
    wx.showModal({
      title: '修改姓名',
      editable: true,
      placeholderText: '请输入姓名',
      content: this.data.user.name || '',
      success: (res) => {
        if (res.confirm && res.content !== undefined) this._set('name', res.content);
      }
    });
  },

  pickAvatar() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      success: async (res) => {
        try {
          const { url } = await upload(res.tempFiles[0].tempFilePath);
          this._set('avatar', API_BASE + url);
        } catch (e) {
          toastError(e);
        }
      }
    });
  },

  pickGender(e) {
    this._set('gender', e.currentTarget.dataset.g);
  },

  pickBirthday(e) {
    this._set('birthday', e.detail.value);
  },

  pickRegion(e) {
    this._set('region', e.detail.value.join(' '));
  },

  toggleReco() {
    this._set('reco', !this.data.user.reco, 'reco_enabled');
  },

  goAddress() {
    wx.navigateTo({ url: '/pages/address/address' });
  }
});
