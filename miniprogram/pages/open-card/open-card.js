const api = require('../../utils/api.js');

Page({
  data: { form: { name: '', phone: '', gender: '男士', birthday: '' }, submitting: false },

  onLoad() {
    api.me().then((u) => {
      this.setData({ form: { name: u.name || '', phone: u.phone || '', gender: u.gender || '男士', birthday: u.birthday || '' } });
    }).catch(() => {});
  },

  onInput(e) { this.setData({ ['form.' + e.currentTarget.dataset.k]: e.detail.value }); },
  pickGender(e) { this.setData({ 'form.gender': e.currentTarget.dataset.g }); },
  pickBirthday(e) { this.setData({ 'form.birthday': e.detail.value }); },

  async submit() {
    const f = this.data.form;
    if (!f.name) return wx.showToast({ title: '请填写称呼', icon: 'none' });
    if (this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      // phone 一并提交——之前漏了它，用户填的号码被静默丢弃，资料页永远显示未填写
      await api.updateMe({ name: f.name, phone: f.phone, gender: f.gender, birthday: f.birthday });
      wx.showToast({ title: '已保存', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 700);
    } catch (e) {
      wx.showToast({ title: (e && e.message) || '提交失败', icon: 'none' });
      this.setData({ submitting: false });
    }
  }
});
