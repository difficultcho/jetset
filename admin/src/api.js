import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from './router.js'

// 生产：页面在 /jetset-admin/，API 在 /jetset/api/...；开发：vite proxy 转发 /api
export const apiBase = import.meta.env.PROD ? '/jetset' : ''

const http = axios.create({ baseURL: apiBase, timeout: 15000 })

http.interceptors.request.use((cfg) => {
  const t = localStorage.getItem('admin_token')
  if (t) cfg.headers.Authorization = 'Bearer ' + t
  return cfg
})

http.interceptors.response.use(
  (res) => {
    if (res.data && res.data.code === 0) return res.data.data
    ElMessage.error((res.data && res.data.message) || '请求失败')
    return Promise.reject(new Error(res.data && res.data.message))
  },
  (err) => {
    const status = err.response && err.response.status
    const msg = err.response && err.response.data && err.response.data.message
    if (status === 401) {
      localStorage.removeItem('admin_token')
      router.push('/login')
    }
    ElMessage.error(msg || '网络错误')
    return Promise.reject(err)
  }
)

// 相对路径图片（/uploads/x.jpg）补全为可访问 URL
export function imgUrl(path) {
  if (!path) return ''
  return path.startsWith('http') ? path : apiBase + path
}

export default http
