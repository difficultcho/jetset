const api = require('../../utils/api.js');

Page({
  data: { form: { name: '', phone: '', gender: '男士', birthday: '' }, agree: true, submitting: false },

  onLoad() {
    api.me().then((u) => {
      this.setData({ form: { name: u.name || '', phone: u.phone || '', gender: u.gender || '男士', birthday: u.birthday || '' } });
    }).catch(() => {});
  },

  onInput(e) { this.setData({ ['form.' + e.currentTarget.dataset.k]: e.detail.value }); },
  pickGender(e) { this.setData({ 'form.gender': e.currentTarget.dataset.g }); },
  pickBirthday(e) { this.setData({ 'form.birthday': e.detail.value }); },
  toggleAgree() { this.setData({ agree: !this.data.agree }); },

  async submit() {
    const f = this.data.form;
    if (!f.name) return wx.showToast({ title: '请填写姓名', icon: 'none' });
    if (!f.phone) return wx.showToast({ title: '请填写手机号', icon: 'none' });
    if (!this.data.agree) return wx.showToast({ title: '请阅读并同意会员声明', icon: 'none' });
    if (this.data.submitting) return;
    this.setData({ submitting: true });
    try {
      await api.updateMe({ name: f.name, gender: f.gender, birthday: f.birthday });
      wx.showToast({ title: '开卡成功', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 700);
    } catch (e) {
      wx.showToast({ title: (e && e.message) || '提交失败', icon: 'none' });
      this.setData({ submitting: false });
    }
  }
});
