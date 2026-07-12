const api = require('../../utils/api.js');
const { toStore } = require('../../utils/mapper.js');

Page({
  data: { stores: [], provs: [], cities: {}, prov: '', city: '', provOpen: false, cityOpen: false, list: [] },

  async onLoad() {
    try {
      const [stores, regions] = await Promise.all([api.stores(), api.storeRegions()]);
      const list = stores.map(toStore);
      this.all = list;
      this.setData({ stores: list, list, provs: regions.provinces, cities: regions.cities });
    } catch (e) { /* 静默 */ }
  },

  toggleProv() { this.setData({ provOpen: !this.data.provOpen, cityOpen: false }); },
  toggleCity() { this.setData({ cityOpen: !this.data.cityOpen, provOpen: false }); },
  pickProv(e) {
    this.setData({ prov: e.currentTarget.dataset.v, city: '', provOpen: false });
    this.filter();
  },
  pickCity(e) {
    this.setData({ city: e.currentTarget.dataset.v, cityOpen: false });
    this.filter();
  },
  filter() {
    const { prov, city } = this.data;
    this.setData({ list: this.all.filter((s) => (!prov || s.province === prov) && (!city || s.city === city)) });
  },
  call(e) { wx.makePhoneCall({ phoneNumber: e.currentTarget.dataset.tel }); },
  goDetail(e) { wx.navigateTo({ url: '/pages/store-detail/store-detail?id=' + e.currentTarget.dataset.id }); }
});
