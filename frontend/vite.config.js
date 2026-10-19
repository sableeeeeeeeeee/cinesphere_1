import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev server proxies /api to FastAPI so the refresh-token cookie is same-origin (no CORS/cookie headaches).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': 'http://localhost:8000' } },
})
