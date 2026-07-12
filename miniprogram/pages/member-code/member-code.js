const api = require('../../utils/api.js');

// 伪随机条形码宽度（演示）
function bars() {
  let r = 7;
  const rnd = () => ((r = (r * 9301 + 49297) % 233280) / 233280);
  const a = [];
  for (let i = 0; i < 46; i++) a.push((1 + Math.floor(rnd() * 3)) * 3);
  return a;
}

Page({
  data: { name: '', code: 'AURL037946', bars: bars(), qr: [] },

  onLoad() {
    // 生成 21×21 伪二维码点阵（演示）
    let r = 13;
    const rnd = () => ((r = (r * 1103515245 + 12345) % 2147483648) / 2147483648);
    const grid = [];
    for (let y = 0; y < 21; y++) {
      const row = [];
      for (let x = 0; x < 21; x++) {
        const corner = (x < 7 && y < 7) || (x > 13 && y < 7) || (x < 7 && y > 13);
        row.push(corner ? ((x === 0 || x === 6 || y === 0 || y === 6 || (x >= 2 && x <= 4 && y >= 2 && y <= 4) || (x >= 14 && (x === 14 || x === 20) ) ) ? 1 : (x >= 14 ? (y === 0 || y === 6 ? 1 : (x === 14 || x === 20 ? 1 : (x >= 16 && x <= 18 && y >= 2 && y <= 4 ? 1 : 0))) : 0)) : (rnd() > 0.55 ? 1 : 0));
      }
      grid.push(row);
    }
    this.setData({ qr: grid });
    api.me().then((u) => this.setData({ name: u.name || 'AURELLE', code: 'AURL' + String(37946 + (u.id || 0)).padStart(6, '0') })).catch(() => {});
  }
});
