// 打开微信官方确认收货组件。结果以组件回调为准，不在这里改订单。
const CONFIRM_APPID = 'wx1183b055aeec94d1';

function openConfirm(receipt) {
  return new Promise((resolve, reject) => {
    if (!wx.openBusinessView) {
      reject(new Error('请升级微信后确认收货'));
      return;
    }
    if (!receipt || !receipt.transaction_id || !receipt.merchant_id || !receipt.merchant_trade_no) {
      reject(new Error('无法打开微信确认收货'));
      return;
    }
    const app = getApp();
    let settled = false;
    const finish = (err) => {
      if (settled) return;
      settled = true;
      app.globalData.wechatConfirmWait = null;
      if (err) reject(err);
      else resolve();
    };
    app.globalData.wechatConfirmWait = {
      resolve: () => finish(null),
      reject: (err) => finish(err)
    };
    wx.openBusinessView({
      businessType: 'weappOrderConfirm',
      extraData: {
        transaction_id: receipt.transaction_id,
        merchant_id: receipt.merchant_id,
        merchant_trade_no: receipt.merchant_trade_no
      },
      success(res) {
        const status = res && res.extraData && res.extraData.status;
        if (!status) return;
        if (status === 'success') finish(null);
        else if (status === 'fail') finish(new Error('确认收货失败'));
        else finish(cancelError());
      },
      fail() {
        finish(new Error('无法打开微信确认收货'));
      }
    });
  });
}

function cancelError() {
  const err = new Error('已取消');
  err.cancel = true;
  return err;
}

function takeConfirmResult(options) {
  const app = getApp();
  const wait = app.globalData.wechatConfirmWait;
  if (!wait) return;
  const ref = (options && options.referrerInfo) || {};
  if (ref.appId !== CONFIRM_APPID) return;
  const extra = ref.extraData || {};
  if (extra.status === 'success') wait.resolve();
  else if (extra.status === 'fail') wait.reject(new Error('确认收货失败'));
  else wait.reject(cancelError());
}

module.exports = { openConfirm, takeConfirmResult, CONFIRM_APPID };
