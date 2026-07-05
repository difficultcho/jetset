const { request } = require('./request.js');

const api = {
  // 商品浏览
  home: () => request('GET', '/api/v1/home'),
  categories: () => request('GET', '/api/v1/categories'),
  products: (params) => {
    const q = Object.keys(params || {})
      .filter((k) => params[k] !== undefined && params[k] !== '')
      .map((k) => k + '=' + encodeURIComponent(params[k]))
      .join('&');
    return request('GET', '/api/v1/products' + (q ? '?' + q : ''));
  },
  productDetail: (id) => request('GET', '/api/v1/products/' + id),

  // 购物车
  cartList: () => request('GET', '/api/v1/cart'),
  cartAdd: (skuId, qty) => request('POST', '/api/v1/cart/items', { sku_id: skuId, qty }),
  cartPatch: (itemId, qty) => request('PATCH', '/api/v1/cart/items/' + itemId, { qty }),
  cartDelete: (itemId) => request('DELETE', '/api/v1/cart/items/' + itemId),

  // 订单
  orderPreview: (items) => request('POST', '/api/v1/orders/preview', { items }),
  orderCreate: (items, addressId, note) =>
    request('POST', '/api/v1/orders', { items, address_id: addressId, note: note || '' }),
  orders: (status, page) =>
    request('GET', '/api/v1/orders?page_size=50' + (status ? '&status=' + status : '') + (page ? '&page=' + page : '')),
  orderCancel: (id) => request('POST', '/api/v1/orders/' + id + '/cancel'),
  orderConfirm: (id) => request('POST', '/api/v1/orders/' + id + '/confirm'),
  orderPay: (id) => request('POST', '/api/v1/orders/' + id + '/pay'),
  mockPayConfirm: (orderNo) => request('POST', '/api/v1/payments/mock/confirm', { order_no: orderNo }),

  // 地址
  addresses: () => request('GET', '/api/v1/addresses'),
  addressCreate: (data) => request('POST', '/api/v1/addresses', data),
  addressUpdate: (id, data) => request('PUT', '/api/v1/addresses/' + id, data),

  // 个人信息
  me: () => request('GET', '/api/v1/me'),
  updateMe: (data) => request('PUT', '/api/v1/me', data),

  // 批发合作
  wholesaleApply: (data) => request('POST', '/api/v1/wholesale/applications', data),
};

module.exports = api;
