// 后端地址：开发者工具 → 本地后端（需勾选「不校验合法域名」）；
// 真机（预览/体验版/正式版）→ 云端（nginx /jetset/ 前缀反代）
const LOCAL = 'http://127.0.0.1:8000';
const PROD = 'https://bce.kkmsee.com/jetset';

// 素材 CDN 域名：COS 加速域名配好后填入（如 'https://cdn.kkmsee.com'），
// 并把该域名加进小程序合法域名。留空则素材走 API 域名（由后端本地伺服或 302 到 CDN）。
const CDN = '';

const platform = (wx.getDeviceInfo ? wx.getDeviceInfo() : wx.getSystemInfoSync()).platform;
const API_BASE = platform === 'devtools' ? LOCAL : PROD;
const ASSET_BASE = platform === 'devtools' ? LOCAL : (CDN || PROD);

module.exports = { API_BASE, ASSET_BASE };
