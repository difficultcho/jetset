const api = require('../../utils/api.js');
const { upload, toastError } = require('../../utils/request.js');

Page({
  data: {
    done: false,
    submitting: false,
    types: ['经销商', '分销商', '门店合作', '其他'],
    form: { type: '', phone: '15501147281', company: '', region: '' },
    license: '',        // 本地预览路径
    store: '',
    licenseUrl: '',     // 上传后的服务端 URL
    storeUrl: ''
  },

  onShow() {
    if (typeof this.getTabBar === 'function') this.getTabBar().refresh(3);
    getApp().refreshCartCount().then(() => {
      if (typeof this.getTabBar === 'function') this.getTabBar().refresh(3);
    });
  },

  pickType(e) {
    this.setData({ 'form.type': this.data.types[e.detail.value] });
  },

  pickRegion(e) {
    this.setData({ 'form.region': e.detail.value.join(' ') });
  },

  onInput(e) {
    this.setData({ ['form.' + e.currentTarget.dataset.k]: e.detail.value });
  },

  chooseImg(e) {
    const k = e.currentTarget.dataset.k; // 'license' | 'store'
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      success: async (res) => {
        const temp = res.tempFiles[0].tempFilePath;
        this.setData({ [k]: temp });
        try {
          const { url } = await upload(temp);
          this.setData({ [k + 'Url']: url });
        } catch (err) {
          this.setData({ [k]: '', [k + 'Url']: '' });
          toastError(err);
        }
      }
    });
  },

  async submit() {
    const { form, licenseUrl, storeUrl, submitting } = this.data;
    if (submitting) return;
    if (!form.type) return wx.showToast({ title: '请选择申请类型', icon: 'none' });
    if (!form.phone) return wx.showToast({ title: '请填写联系方式', icon: 'none' });
    if (!form.company) return wx.showToast({ title: '请填写公司名称', icon: 'none' });
    if (!form.region) return wx.showToast({ title: '请选择所在地区', icon: 'none' });
    if (!licenseUrl || !storeUrl) return wx.showToast({ title: '请上传营业执照和门店照片', icon: 'none' });

    this.setData({ submitting: true });
    try {
      await api.wholesaleApply({
        type: form.type,
        phone: form.phone,
        company: form.company,
        region: form.region,
        license_img: licenseUrl,
        store_img: storeUrl
      });
      this.setData({ done: true, submitting: false });
    } catch (e) {
      toastError(e);
      this.setData({ submitting: false });
    }
  },

  again() {
    this.setData({
      done: false,
      form: { type: '', phone: this.data.form.phone, company: '', region: '' },
      license: '', store: '', licenseUrl: '', storeUrl: ''
    });
  }
});
