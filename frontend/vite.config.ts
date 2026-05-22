import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: process.env.VITE_WS_BASE_URL || 'ws://localhost:8000',
        ws: true
      },
      '/downloads': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true
      },
      '/static': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 5000,
    host: '0.0.0.0',
    strictPort: true
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-vue': ['vue', 'vue-router', 'pinia'],
          'vendor-ui': ['@headlessui/vue', '@heroicons/vue'],
          'vendor-utils': ['axios', 'date-fns', 'chart.js', 'vue-chartjs']
        }
      }
    }
  }
})
