const api = require('./api.js');
const { openConfirm } = require('./wechat-receipt.js');

function cancelError() {
  const err = new Error('已取消');
  err.cancel = true;
  return err;
}

function confirmOrder(order) {
  if (order && order.wechatReceipt) {
    return openConfirm(order.wechatReceipt).then(() => api.orderConfirm(order.orderNo));
  }
  return new Promise((resolve, reject) => {
    wx.showModal({
      title: '确认收货',
      content: '确认已收到商品？',
      success: (r) => {
        if (!r.confirm) {
          reject(cancelError());
          return;
        }
        api.orderConfirm(order.orderNo).then(resolve, reject);
      },
      fail: () => reject(cancelError())
    });
  });
}

module.exports = { confirmOrder };
