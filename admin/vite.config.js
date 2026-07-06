import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // 部署在 nginx /jetset-admin/ 子路径下
  base: '/jetset-admin/',
  server: {
    port: 5174,
    // 本地开发直连本地后端
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/uploads': 'http://127.0.0.1:8000'
    }
  }
})
