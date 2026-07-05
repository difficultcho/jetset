// 后端地址：开发者工具 → 本地后端（需勾选「不校验合法域名」）；
// 真机（预览/体验版/正式版）→ 云端（nginx /jetset/ 前缀反代）
const LOCAL = 'http://127.0.0.1:8000';
const PROD = 'https://bce.kkmsee.com/jetset';

const platform = (wx.getDeviceInfo ? wx.getDeviceInfo() : wx.getSystemInfoSync()).platform;
const API_BASE = platform === 'devtools' ? LOCAL : PROD;

module.exports = { API_BASE };
