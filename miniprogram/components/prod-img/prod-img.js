// 商品占位图：品牌小字 + 色块圆形（设计稿说明其并非最终商品图，接入真实图片后替换本组件内部实现）
Component({
  properties: {
    prod: { type: Object, value: null },
    ci: { type: Number, value: 0 },
    // 设计稿基准宽度（px），仅用于控制中心圆形图案的比例
    size: { type: Number, value: 80 }
  },
  data: { c: '#888888' },
  observers: {
    'prod, ci'(prod, ci) {
      if (!prod || !prod.sw) return;
      this.setData({ c: prod.sw[Math.min(ci, prod.sw.length - 1)] });
    }
  }
});
