// 商品图：优先展示真实商品图（prod.img 或按颜色 prod.imgs[ci]），
// 无图时回退为设计稿约定的占位图案（品牌小字 + 色块圆形）
Component({
  properties: {
    prod: { type: Object, value: null },
    ci: { type: Number, value: 0 },
    // 设计稿基准宽度（px），仅用于控制占位图案中心圆形的比例
    size: { type: Number, value: 80 }
  },
  data: { c: '#888888', src: '' },
  observers: {
    'prod, ci'(prod, ci) {
      if (!prod) return;
      const sw = prod.sw || ['#888888'];
      const src = (prod.imgs && prod.imgs[ci]) || prod.img || '';
      this.setData({ c: sw[Math.min(ci, sw.length - 1)], src });
    }
  }
});
