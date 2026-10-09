import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = process.env.API_PROXY_TARGET?.trim() || env.API_PROXY_TARGET?.trim() || 'http://127.0.0.1:8000'
  return {
    plugins: [vue()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      // Windows-mounted files may not emit reliable WSL filesystem notifications.
      watch: { usePolling: true, interval: 500 },
      proxy: { '/api': { target, changeOrigin: true } },
    },
  }
})



