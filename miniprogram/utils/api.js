const { request } = require('./request.js');

const api = {
  // 商品浏览
  home: () => request('GET', '/api/v1/home'),
  page: (key) => request('GET', '/api/v1/pages/' + key),
  categories: () => request('GET', '/api/v1/categories'),
  products: (params) => {
    const q = Object.keys(params || {})
      .filter((k) => params[k] !== undefined && params[k] !== '')
      .map((k) => k + '=' + encodeURIComponent(params[k]))
      .join('&');
    return request('GET', '/api/v1/products' + (q ? '?' + q : ''));
  },
  productDetail: (id) => request('GET', '/api/v1/products/' + id),
  series: () => request('GET', '/api/v1/series'),

  // 门店
  stores: (province, city) => request('GET', '/api/v1/stores' +
    (province || city ? '?' + [province && 'province=' + encodeURIComponent(province), city && 'city=' + encodeURIComponent(city)].filter(Boolean).join('&') : '')),
  storeRegions: () => request('GET', '/api/v1/stores/regions'),
  storeDetail: (id) => request('GET', '/api/v1/stores/' + id),


  // 购物车
  cartList: () => request('GET', '/api/v1/cart'),
  cartAdd: (skuId, qty) => request('POST', '/api/v1/cart/items', { sku_id: skuId, qty }),
  cartPatch: (itemId, qty) => request('PATCH', '/api/v1/cart/items/' + itemId, { qty }),
  cartDelete: (itemId) => request('DELETE', '/api/v1/cart/items/' + itemId),

  // 订单
  orderPreview: (items, userCouponId, usePoints) =>
    request('POST', '/api/v1/orders/preview', {
      items, user_coupon_id: userCouponId || null, use_points: !!usePoints
    }),
  orderCreate: (items, addressId, note, userCouponId, usePoints) =>
    request('POST', '/api/v1/orders', {
      items, address_id: addressId, note: note || '',
      user_coupon_id: userCouponId || null, use_points: !!usePoints
    }),
  orders: (status, page) =>
    request('GET', '/api/v1/orders?page_size=50' + (status ? '&status=' + status : '') + (page ? '&page=' + page : '')),
  orderDetail: (id) => request('GET', '/api/v1/orders/' + id),
  orderCancel: (id) => request('POST', '/api/v1/orders/' + id + '/cancel'),
  orderConfirm: (id) => request('POST', '/api/v1/orders/' + id + '/confirm'),
  orderPay: (id) => request('POST', '/api/v1/orders/' + id + '/pay'),
  mockPayConfirm: (orderNo) => request('POST', '/api/v1/payments/mock/confirm', { order_no: orderNo }),

  // 地址
  addresses: () => request('GET', '/api/v1/addresses'),
  addressCreate: (data) => request('POST', '/api/v1/addresses', data),
  addressUpdate: (id, data) => request('PUT', '/api/v1/addresses/' + id, data),
  addressDelete: (id) => request('DELETE', '/api/v1/addresses/' + id),
  addressSetDefault: (id) => request('PUT', '/api/v1/addresses/' + id + '/default'),

  // 个人信息
  me: () => request('GET', '/api/v1/me'),
  updateMe: (data) => request('PUT', '/api/v1/me', data),

  // 优惠券
  couponsCenter: () => request('GET', '/api/v1/coupons/center'),
  couponClaim: (id) => request('POST', '/api/v1/coupons/' + id + '/claim'),
  myCoupons: (status) => request('GET', '/api/v1/me/coupons' + (status ? '?status=' + status : '')),

  // 积分
  pointsLogs: () => request('GET', '/api/v1/me/points/logs'),

  // 批发合作
  wholesaleApply: (data) => request('POST', '/api/v1/wholesale/applications', data),
};

module.exports = api;
