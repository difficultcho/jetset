const api = require('../../utils/api.js');
const { toOrder, toProd } = require('../../utils/mapper.js');
const { toastError } = require('../../utils/request.js');

const TABS = [
  { label: '全部', status: '' },
  { label: '待付款', status: 'pending_payment' },
  { label: '待发货', status: 'pending_shipment' },
  { label: '待收货', status: 'pending_receipt' },
  { label: '待评价', status: 'pending_review' }
];

Page({
  data: {
    tabs: TABS.map((t) => t.label),
    fi: 0,
    list: [],
    recs: [],
    loaded: false
  },

  onShow() {
    this.fetch();
  },

  async fetch() {
    try {
      const page = await api.orders(TABS[this.data.fi].status);
      this.setData({ list: page.items.map(toOrder), loaded: true });
      if (!page.items.length && !this.data.recs.length) {
        const prods = await api.products({ page_size: 4 });
        this.setData({ recs: prods.items.map(toProd) });
      }
    } catch (e) {
      toastError(e);
    }
  },

  pickF(e) {
    this.setData({ fi: e.currentTarget.dataset.i }, () => this.fetch());
  },

  async cancel(e) {
    const id = e.currentTarget.dataset.id;
    const r = await new Promise((resolve) => wx.showModal({ title: '取消订单', content: '确定取消该订单吗？', success: resolve }));
    if (!r.confirm) return;
    try {
      await api.orderCancel(id);
      wx.showToast({ title: '已取消', icon: 'success' });
      this.fetch();
    } catch (err) {
      toastError(err);
    }
  },

  // 模拟支付：拉起支付（mock 渠道）→ 回调确认 → 订单变为待发货
  async pay(e) {
    const { id, no } = e.currentTarget.dataset;
    try {
      await api.orderPay(id);
      await api.mockPayConfirm(no);
      wx.showToast({ title: '支付成功（模拟）', icon: 'success' });
      this.fetch();
    } catch (err) {
      toastError(err);
    }
  },

  async confirmReceipt(e) {
    try {
      await api.orderConfirm(e.currentTarget.dataset.id);
      wx.showToast({ title: '已确认收货', icon: 'success' });
      this.fetch();
    } catch (err) {
      toastError(err);
    }
  },

  goShop() {
    wx.switchTab({ url: '/pages/shop/shop' });
  }
});
