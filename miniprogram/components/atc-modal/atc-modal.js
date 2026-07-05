// 商品配置选择弹窗（bottom sheet）：选择颜色/尺码后解析出 SKU，加入购物车或立即购买
Component({
  properties: {
    prod: { type: Object, value: null }, // mapper.toDetail 的形状（含 skus）
    mode: { type: String, value: 'cart' } // 'cart' | 'buy'
  },
  data: { ci: 0, si: -1, hint: '', ok: false },
  observers: {
    prod(prod) {
      if (!prod) return;
      // 仅 1 种尺码时默认选中；多种时必须用户选择
      const si = prod.sizes.length === 1 ? 0 : -1;
      let hint = '请选择';
      if (prod.colors.length > 1) hint += ' 颜色';
      if (prod.sizes.length > 1) hint += ' 尺码';
      this.setData({ ci: 0, si, hint, ok: si >= 0 });
    }
  },
  methods: {
    close() {
      this.triggerEvent('close');
    },
    noop() {},
    pickColor(e) {
      this.setData({ ci: e.currentTarget.dataset.i });
    },
    pickSize(e) {
      this.setData({ si: e.currentTarget.dataset.i, ok: true });
    },
    confirm() {
      const { prod, ci, si, ok } = this.data;
      if (!ok) return;
      const size = prod.sizes[Math.max(si, 0)];
      const sku = (prod.skus || []).find((s) => s.color_index === ci && s.size === size);
      if (!sku) {
        wx.showToast({ title: '该规格暂不可售', icon: 'none' });
        return;
      }
      if (sku.stock < 1) {
        wx.showToast({ title: '该规格暂时缺货', icon: 'none' });
        return;
      }
      this.triggerEvent('confirm', { skuId: sku.id, ci, si: Math.max(si, 0), qty: 1 });
    }
  }
});
