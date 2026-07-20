// 后端数据 → JET SET 视图模型。后端金额单位为「分」，展示用「元」（千分位）。
const { ASSET_BASE } = require('./config.js');

function yuan(cents) {
  return (cents || 0) / 100;
}

// 分 → "2,399"（整数）或 "2,399.50"
function fmt(cents) {
  const v = yuan(cents);
  const s = Number.isInteger(v) ? String(v) : v.toFixed(2);
  const [int, dec] = s.split('.');
  const withSep = int.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return dec ? withSep + '.' + dec : withSep;
}

function fullImg(path) {
  if (!path) return '';
  return path.indexOf('http') === 0 ? path : ASSET_BASE + path;
}

// 商品卡（首页/商城/列表/心愿单/足迹/推荐）
function toCard(p) {
  const hasSale = !!p.original_price && p.original_price > p.price;
  return {
    id: p.id,
    name: p.name,
    sub: p.sub || p.name,
    en: p.series_en || p.code || '',   // 卡片/走马灯小字标：优先系列 en
    seriesEn: p.series_en || '',
    price: yuan(p.price),
    priceText: fmt(p.price),
    sale: hasSale,
    saleText: hasSale ? fmt(p.original_price) : '',
    badge: p.badge || '',
    sw: p.color_hexes && p.color_hexes.length ? p.color_hexes : ['#c9b79b'],
    colorHex: (p.color_hexes && p.color_hexes[0]) || '#c9b79b',
    img: fullImg(p.image)
  };
}

// 配置化页面块（/pages/{key} 返回的已解析块 → 渲染视图模型）
function toPageBlocks(blocks) {
  return (blocks || []).map((b, i) => {
    const o = { bkey: i, kind: b.kind, ratio: b.ratio || '', inset: !!b.inset, link: b.link || null };
    if (b.kind === 'image') {
      o.img = fullImg(b.img);
    } else if (b.kind === 'video') {
      o.src = fullImg(b.src);
      o.poster = b.poster ? fullImg(b.poster) : '';
      o.vid = 'vb' + i;
    } else if (b.kind === 'text') {
      o.preset = b.preset || 'para';
      o.text = b.text || '';
      o.align = b.align || 'left';
    } else if (b.kind === 'linkrow') {
      o.left = b.left ? { text: b.left.text, link: b.left.link || null } : null;
      o.right = b.right ? { text: b.right.text, link: b.right.link || null } : null;
    } else if (b.kind === 'carousel') {
      o.items = (b.items || []).map(toCard);
      o.idx = 0;
    }
    return o;
  });
}

// 商品详情
function toDetail(d) {
  const imgs = d.colors.map((c) => fullImg(c.image));
  // 每色全部图（多图轮播）；无 images 时回退单图
  const imgsList = d.colors.map((c) => {
    const list = (c.images && c.images.length ? c.images : (c.image ? [c.image] : []));
    return list.map(fullImg);
  });
  const hasSale = !!d.original_price && d.original_price > d.price;
  return {
    id: d.id,
    name: d.name,
    sub: d.sub || d.name,
    en: (d.series && d.series.en) || d.code || '',
    price: yuan(d.price),
    priceText: fmt(d.price),
    sale: hasSale,
    origText: hasSale ? fmt(d.original_price) : '',
    desc: d.brief,
    detailText: d.detail,
    bullets: d.bullets || [],
    code: d.code || d.en_model || ('AU' + d.id),
    hasVideo: !!d.has_video,
    series: d.series || null,
    colors: d.colors.map((c) => c.name),
    sw: d.colors.map((c) => c.hex),
    imgs,
    imgsList,
    img: imgs.find((u) => u) || '',
    sizes: d.sizes,
    skus: d.skus
  };
}

// 门店
function toStore(s) {
  return {
    id: s.id, name: s.name, short: s.short_name || s.name,
    province: s.province, city: s.city, addr: s.address, tel: s.tel,
    hours: s.business_hours, images: (s.images || []).map(fullImg), qr: fullImg(s.consultant_qr),
    lat: s.lat, lng: s.lng
  };
}

// 品牌内容（详情含 series 关联与子项目卡片）

function toCartItem(it) {
  return {
    id: it.id,
    skuId: it.sku_id,
    qty: it.qty,
    name: it.name,
    spec: it.color_name + ' / ' + it.size,
    price: yuan(it.price),
    priceText: fmt(it.price),
    stock: it.stock,
    prod: { en: it.en_model, sw: [it.color_hex || '#c9b79b'], img: fullImg(it.image) }
  };
}

function toOrderLine(it) {
  return {
    skuId: it.sku_id,
    qty: it.qty,
    name: it.name,
    spec: it.color_name + ' / ' + it.size,
    price: yuan(it.price),
    priceText: fmt(it.price),
    prod: { en: it.en_model, sw: [it.color_hex || '#c9b79b'], img: fullImg(it.image) }
  };
}

function toOrder(o) {
  return {
    id: o.id,
    orderNo: o.order_no,
    status: o.status,
    statusLabel: o.status_label,
    payAmount: yuan(o.pay_amount),
    payText: fmt(o.pay_amount),
    itemText: fmt(o.item_amount),
    createdAt: (o.created_at || '').replace('T', ' ').slice(0, 19),
    expireAt: o.expire_at,
    shipment: o.shipment || null,
    items: o.items.map(toOrderLine),
    itemCount: o.items.reduce((s, i) => s + i.qty, 0)
  };
}

function toAddress(a) {
  return {
    id: a.id,
    name: a.name,
    phone: a.phone,
    full: (a.region ? a.region + ' ' : '') + a.detail,
    isDefault: a.is_default
  };
}

// 优惠券（附属功能页复用）
function toCoupon(c) {
  return {
    id: c.id,
    name: c.name,
    amount: yuan(c.amount),
    thresholdText: c.threshold > 0 ? '满' + yuan(c.threshold) + '可用' : '无门槛',
    status: c.status || '',
    usable: c.usable !== false,
    expiresText: c.expires_at ? String(c.expires_at).slice(0, 10) + ' 前有效'
      : c.valid_days ? '领取后 ' + c.valid_days + ' 天内有效'
      : c.valid_until ? String(c.valid_until).slice(0, 10) + ' 前有效' : '',
    claimable: c.claimable,
    soldOut: c.sold_out,
    claimed: c.claimed || 0
  };
}

module.exports = {
  yuan, fmt, fullImg, toCard, toPageBlocks, toDetail, toCartItem, toOrderLine, toOrder,
  toAddress, toCoupon, toStore
};
