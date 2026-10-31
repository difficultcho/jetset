// 门店没上传导购码时，在页面上画一张结构完整的二维码。
// 定位符、分隔、时序、对齐、格式信息按版本 6 的位置摆放。
// 数据区用门店编号做种子，所以每家店图案固定且互不相同；扫出来不是链接。

const VERSION = 6;
const SIZE = 21 + (VERSION - 1) * 4;
const QUIET = 4;
const ALIGN = [6, 34];
// 纠错 M、掩码 0–7 的格式信息，已按规范异或过。
const FORMAT = [21522, 20773, 24188, 23371, 17913, 16590, 20375, 19104];

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function seedFrom(id) {
  const s = String(id);
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function blank() {
  const rows = [];
  for (let r = 0; r < SIZE; r++) {
    const row = [];
    for (let c = 0; c < SIZE; c++) row.push(null);
    rows.push(row);
  }
  return rows;
}

function set(m, r, c, v) {
  if (r < 0 || c < 0 || r >= SIZE || c >= SIZE) return;
  m[r][c] = v;
}

function finder(m, row, col) {
  for (let r = -1; r <= 7; r++) {
    for (let c = -1; c <= 7; c++) {
      const edge = (r >= 0 && r <= 6 && (c === 0 || c === 6))
        || (c >= 0 && c <= 6 && (r === 0 || r === 6));
      const core = r >= 2 && r <= 4 && c >= 2 && c <= 4;
      set(m, row + r, col + c, edge || core);
    }
  }
}

function timing(m) {
  for (let i = 8; i < SIZE - 8; i++) {
    if (m[i][6] === null) m[i][6] = i % 2 === 0;
    if (m[6][i] === null) m[6][i] = i % 2 === 0;
  }
}

function align(m) {
  ALIGN.forEach((row) => {
    ALIGN.forEach((col) => {
      if (m[row][col] !== null) return;
      for (let r = -2; r <= 2; r++) {
        for (let c = -2; c <= 2; c++) {
          const edge = r === -2 || r === 2 || c === -2 || c === 2;
          m[row + r][col + c] = edge || (r === 0 && c === 0);
        }
      }
    });
  });
}

function formatInfo(m, bits) {
  for (let i = 0; i < 15; i++) {
    const on = ((bits >> i) & 1) === 1;
    if (i < 6) m[i][8] = on;
    else if (i < 8) m[i + 1][8] = on;
    else m[SIZE - 15 + i][8] = on;
  }
  for (let i = 0; i < 15; i++) {
    const on = ((bits >> i) & 1) === 1;
    if (i < 8) m[8][SIZE - i - 1] = on;
    else if (i < 9) m[8][15 - i - 1 + 1] = on;
    else m[8][15 - i - 1] = on;
  }
  m[SIZE - 8][8] = true;
}

function build(seed) {
  const m = blank();
  finder(m, 0, 0);
  finder(m, SIZE - 7, 0);
  finder(m, 0, SIZE - 7);
  align(m);
  timing(m);
  const rng = mulberry32(seed);
  formatInfo(m, FORMAT[Math.floor(rng() * FORMAT.length)]);
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (m[r][c] === null) m[r][c] = rng() < 0.5;
    }
  }
  return m;
}

function paintQr(ctx, px, seed) {
  const cells = SIZE + QUIET * 2;
  const mod = Math.max(1, Math.floor(px / cells));
  const span = mod * cells;
  const origin = Math.floor((px - span) / 2);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, px, px);
  ctx.fillStyle = '#111111';
  const matrix = build(seed);
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      if (!matrix[r][c]) continue;
      ctx.fillRect(origin + (c + QUIET) * mod, origin + (r + QUIET) * mod, mod, mod);
    }
  }
}

module.exports = { paintQr, seedFrom, build };
