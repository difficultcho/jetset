// 后端地址：本地联调用 127.0.0.1（需在开发者工具勾选「不校验合法域名」）
// 云端部署后改为备案 HTTPS 域名，并在小程序后台配置 request/uploadFile 合法域名
const API_BASE = 'http://127.0.0.1:8000';
// const API_BASE = 'https://api.你的域名.com';   // 生产/真机

module.exports = { API_BASE };
