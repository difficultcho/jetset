// 后端数据 → 页面视图模型。金额统一：后端返回「分」，展示用「元」。
const { API_BASE } = require('./config.js');

function fen2yuan(cents) {
  const y = (cents || 0) / 100;
  return Number.isInteger(y) ? y : y.toFixed(2);
}

// 相对路径图片（/uploads/x.jpg）补全为完整 URL；空值返回 ''（组件回退占位图案）
function fullImg(path) {
  if (!path) return '';
  return path.indexOf('http') === 0 ? path : API_BASE + path;
}

// 商品列表项（首页/商城/推荐位共用），兼容 prod-img 需要的 {sw, en, img} 形状
function toProd(p) {
  return {
    id: p.id,
    name: p.name,
    en: p.en_model,
    price: fen2yuan(p.price),
    badge: p.badge || '',
    sw: p.color_hexes && p.color_hexes.length ? p.color_hexes : ['#888888'],
    img: fullImg(p.image),
  };
}

// 商品详情
function toDetail(d) {
  const imgs = d.colors.map((c) => fullImg(c.image));
  return {
    id: d.id,
    name: d.name,
    en: d.en_model,
    price: fen2yuan(d.price),
    badge: d.badge || '',
    desc: d.brief,
    detailText: d.detail,
    colors: d.colors.map((c) => c.name),
    sw: d.colors.map((c) => c.hex),
    imgs, // 每个颜色一张图，切色联动
    img: imgs.find((u) => u) || '',
    sizes: d.sizes,
    skus: d.skus, // [{id, color_index, size, price, stock}]
  };
}

// 购物车行
function toCartItem(it) {
  return {
    id: it.id,
    skuId: it.sku_id,
    qty: it.qty,
    name: it.name,
    spec: it.color_name + '，' + it.size,
    price: fen2yuan(it.price),
    stock: it.stock,
    prod: { en: it.en_model, sw: [it.color_hex || '#888888'], img: fullImg(it.image) },
  };
}

// 订单行（preview 与 order.items 结构一致）
function toOrderLine(it) {
  return {
    skuId: it.sku_id,
    qty: it.qty,
    name: it.name,
    spec: it.color_name + '；' + it.size,
    price: fen2yuan(it.price),
    prod: { en: it.en_model, sw: [it.color_hex || '#888888'], img: fullImg(it.image) },
  };
}

function toOrder(o) {
  return {
    id: o.id,
    orderNo: o.order_no,
    status: o.status,
    statusLabel: o.status_label,
    payAmount: fen2yuan(o.pay_amount),
    itemAmount: fen2yuan(o.item_amount),
    shipment: o.shipment || null, // {company, tracking_no}
    items: o.items.map(toOrderLine),
  };
}

function toAddress(a) {
  return {
    id: a.id,
    name: a.name,
    phone: a.phone,
    address: (a.region ? a.region + ' ' : '') + a.detail,
    isDefault: a.is_default,
  };
}

module.exports = { fen2yuan, toProd, toDetail, toCartItem, toOrderLine, toOrder, toAddress };
