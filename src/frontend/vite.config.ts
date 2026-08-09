import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 前端只对接 gateway(:8000)。开发期通过 vite 代理把 /api 转发到 gateway，
// 生产由 nginx 反代。envPrefix 同时支持 REACT_APP_（任务约定）与 VITE_（Vite 默认）。
export default defineConfig({
  plugins: [react()],
  envPrefix: ['VITE_', 'REACT_APP_'],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
});
