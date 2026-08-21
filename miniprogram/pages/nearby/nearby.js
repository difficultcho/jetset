const api = require('../../utils/api.js');
const { toStore } = require('../../utils/mapper.js');

// 下拉里的「不限」项：选中即把该级筛选置空。后端返回的国家/城市列表里没有这一项，
// 缺了它用户选完就再也回不到「看全部门店」的状态，只能退出页面重进。
const ANY = '';

Page({
  data: {
    list: [],                        // 当前展示的门店（筛选结果）
    countries: [], cities: {},       // 下拉数据源，cities 按国家分组
    country: '', city: '',           // 已选筛选值，空 = 不限
    countryOpen: false, cityOpen: false
  },

  async onLoad() {
    try {
      const [stores, regions] = await Promise.all([api.stores(), api.storeRegions()]);
      this.all = stores.map(toStore);
      this.setData({
        list: this.all,
        countries: regions.countries || [],
        cities: regions.cities || {}
      });
    } catch (e) { /* 静默：列表留空 */ }
  },

  toggleCountry() {
    this.setData({ countryOpen: !this.data.countryOpen, cityOpen: false });
  },
  toggleCity() {
    // 城市依附于国家：没选国家就没有可选项，直接给反馈而不是静默打开一个空弹层
    if (!this.data.country) return wx.showToast({ title: '请先选择国家/地区', icon: 'none' });
    this.setData({ cityOpen: !this.data.cityOpen, countryOpen: false });
  },

  pickCountry(e) {
    // 换国家必须清空城市：旧城市多半不属于新国家，留着会筛出空列表
    this.setData({ country: e.currentTarget.dataset.v, city: ANY, countryOpen: false });
    this.filter();
  },
  pickCity(e) {
    this.setData({ city: e.currentTarget.dataset.v, cityOpen: false });
    this.filter();
  },

  filter() {
    const { country, city } = this.data;
    this.setData({
      list: this.all.filter((s) => (!country || s.country === country)
                                && (!city || s.city === city))
    });
  },

  call(e) { wx.makePhoneCall({ phoneNumber: e.currentTarget.dataset.tel }); },

  // 用门店 lat/lng 唤起微信内置地图。不涉及用户定位授权——只是把门店标出来。
  openMap(e) {
    const s = this.all.filter((x) => x.id === e.currentTarget.dataset.id)[0];
    if (!s || s.lat == null || s.lng == null) {
      return wx.showToast({ title: '该门店暂无坐标', icon: 'none' });
    }
    wx.openLocation({
      latitude: s.lat, longitude: s.lng, name: s.name, address: s.addr, scale: 16
    });
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/store-detail/store-detail?id=' + e.currentTarget.dataset.id });
  }
});
