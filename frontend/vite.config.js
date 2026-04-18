import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8100'
    }
  },
  build: {
    outDir: '../static',  // 构建产物直接输出到后端静态目录
    emptyOutDir: true,
  },
})