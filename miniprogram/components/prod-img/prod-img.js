// AURELLE 商品图：优先真实图；无图时用暖沙斜纹占位 + 等宽字体标签
Component({
  properties: {
    prod: { type: Object, value: null },
    ci: { type: Number, value: 0 },
    label: { type: String, value: '' }  // 占位标签文字，缺省用商品英文名
  },
  data: { src: '', tint: '#ece5dd', tint2: '#e4dccf', ph: '' },
  observers: {
    'prod, ci, label'(prod, ci, label) {
      if (!prod) return;
      const src = (prod.imgs && prod.imgs[ci]) || prod.img || '';
      // 暖沙色调占位（若有商品色则取其浅化版）
      const hex = (prod.sw && prod.sw[ci]) || prod.colorHex || '';
      let tint = '#ece5dd';
      let tint2 = '#e4dccf';
      if (hex && /^#[0-9a-fA-F]{6}$/.test(hex)) {
        tint = _tint(hex, 0.82);
        tint2 = _tint(hex, 0.72);
      }
      this.setData({ src, tint, tint2, ph: label || prod.en || prod.name || '' });
    }
  }
});

// 将颜色向白色混合，得到浅色调
function _tint(hex, mix) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const m = (c) => Math.round(c + (255 - c) * mix);
  const h = (c) => ('0' + m(c).toString(16)).slice(-2);
  return '#' + h(r) + h(g) + h(b);
}
