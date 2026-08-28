import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Lets `npm run dev` hit the FastAPI backend (run separately, e.g.
    // `uvicorn webapp.backend.main:app --reload`) without CORS setup —
    // production instead serves both from the same FastAPI process.
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
})
