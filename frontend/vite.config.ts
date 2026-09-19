import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Khi chạy phát triển, mọi lời gọi /api được chuyển sang backend ở cổng 8000
// nên frontend và backend dùng chung một địa chỉ, không vướng CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
