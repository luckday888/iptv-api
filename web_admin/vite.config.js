import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 管理端部署在 /admin 子路径
export default defineConfig({
  base: '/admin/',
  plugins: [react()],
  server: {
    port: 5181,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5180',
        changeOrigin: true,
      },
    },
  },
})
