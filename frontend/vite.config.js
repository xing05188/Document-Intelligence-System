import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        ws: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'excel-vendor': ['xlsx'],
          'md-vendor': ['marked', 'highlight.js'],
          'docx-vendor': ['mammoth'],
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
})
