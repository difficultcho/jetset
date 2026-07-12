const api = require('../../utils/api.js');
const { fullImg } = require('../../utils/mapper.js');
const { upload } = require('../../utils/request.js');
const { API_BASE } = require('../../utils/config.js');

Page({
  data: { user: null },

  async onLoad() {
    try {
      const u = await api.me();
      this.setData({ user: { nick: u.name, avatar: u.avatar, phone: u.phone || '未绑定', gender: u.gender || '男士', birthday: u.birthday, region: u.region, email: '' } });
      this.dirty = {};
    } catch (e) { /* 静默 */ }
  },

  onUnload() {
    if (this.dirty && Object.keys(this.dirty).length) api.updateMe(this.dirty).catch(() => {});
  },
  _set(field, value, apiField) {
    this.setData({ ['user.' + field]: value });
    this.dirty[apiField || field] = value;
  },

  onNick(e) { this._set('nick', e.detail.value, 'name'); },
  pickGender(e) { this._set('gender', e.currentTarget.dataset.g, 'gender'); },
  pickBirthday(e) { this._set('birthday', e.detail.value, 'birthday'); },
  pickRegion(e) { this._set('region', e.detail.value.join(' '), 'region'); },
  onEmail(e) { this.setData({ 'user.email': e.detail.value }); },

  pickAvatar() {
    wx.chooseMedia({ count: 1, mediaType: ['image'], success: async (res) => {
      try { const { url } = await upload(res.tempFiles[0].tempFilePath); this._set('avatar', API_BASE + url, 'avatar'); }
      catch (e) { wx.showToast({ title: '上传失败', icon: 'none' }); }
    } });
  },

  async save() {
    try {
      await api.updateMe(this.dirty);
      this.dirty = {};
      wx.showToast({ title: '已保存', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 600);
    } catch (e) { wx.showToast({ title: (e && e.message) || '保存失败', icon: 'none' }); }
  }
});
