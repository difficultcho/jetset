const { API_BASE } = require('./config.js');

let loginPromise = null;

function getToken() {
  return wx.getStorageSync('token') || '';
}

function rawRequest(method, path, data, header) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: API_BASE + path,
      method,
      data,
      header: Object.assign({ 'Content-Type': 'application/json' }, header || {}),
      success: resolve,
      fail: () => reject(new Error('网络请求失败，请检查后端服务')),
    });
  });
}

// 静默登录（并发去重）：wx.login 的 code 换后端 token
function login() {
  if (loginPromise) return loginPromise;
  loginPromise = new Promise((resolve, reject) => {
    wx.login({
      success: (r) => {
        rawRequest('POST', '/api/v1/auth/login', { code: r.code })
          .then((res) => {
            if (res.statusCode === 200 && res.data && res.data.code === 0) {
              wx.setStorageSync('token', res.data.data.token);
              resolve(res.data.data);
            } else {
              reject(new Error((res.data && res.data.message) || '登录失败'));
            }
          })
          .catch(reject);
      },
      fail: () => reject(new Error('微信登录失败')),
    });
  });
  loginPromise.then(() => { loginPromise = null; }, () => { loginPromise = null; });
  return loginPromise;
}

async function ensureLogin() {
  if (!getToken()) await login();
}

/**
 * 统一请求：自动带 token；401 时重新登录并重试一次。
 * 成功返回 data 字段；失败 reject Error(message)。
 */
async function request(method, path, data) {
  await ensureLogin();
  let res = await rawRequest(method, path, data, { Authorization: 'Bearer ' + getToken() });
  if (res.statusCode === 401) {
    wx.removeStorageSync('token');
    await login();
    res = await rawRequest(method, path, data, { Authorization: 'Bearer ' + getToken() });
  }
  if (res.statusCode >= 200 && res.statusCode < 300 && res.data && res.data.code === 0) {
    return res.data.data;
  }
  throw new Error((res.data && res.data.message) || '请求失败（' + res.statusCode + '）');
}

function upload(filePath) {
  return ensureLogin().then(
    () =>
      new Promise((resolve, reject) => {
        wx.uploadFile({
          url: API_BASE + '/api/v1/uploads',
          filePath,
          name: 'file',
          header: { Authorization: 'Bearer ' + getToken() },
          success: (res) => {
            try {
              const d = JSON.parse(res.data);
              if (d.code === 0) resolve(d.data); // { url }
              else reject(new Error(d.message || '上传失败'));
            } catch (e) {
              reject(new Error('上传失败'));
            }
          },
          fail: () => reject(new Error('上传失败')),
        });
      })
  );
}

function toastError(err) {
  wx.showToast({ title: (err && err.message) || '出错了', icon: 'none' });
}

module.exports = { request, upload, ensureLogin, toastError };
