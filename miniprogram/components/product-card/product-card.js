// AURELLE 网格商品卡：图 + 名称 + 价格行（左价右星标/购物袋）
Component({
  properties: {
    prod: { type: Object, value: null },   // { id, name, price, sale, en, img, sw, colorHex }
    wished: { type: Boolean, value: false }
  },
  methods: {
    onTap() {
      this.triggerEvent('tap', { id: this.data.prod.id });
    },
    onStar() {
      this.triggerEvent('star', { id: this.data.prod.id });
    },
    onBag() {
      this.triggerEvent('bag', { id: this.data.prod.id });
    }
  }
});
