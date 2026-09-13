import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/events': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/ingest': 'http://127.0.0.1:8000',
      '/demo': 'http://127.0.0.1:8000',
    },
  },
  preview: {
    port: 5173,
    host: true,
    proxy: {
      '/events': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/ingest': 'http://127.0.0.1:8000',
      '/demo': 'http://127.0.0.1:8000',
    },
  },
})
