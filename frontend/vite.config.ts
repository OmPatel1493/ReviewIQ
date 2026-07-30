import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  // `@tailwindcss/vite` is the Tailwind v4 plugin — no PostCSS config or
  // `tailwind.config.js` needed; utilities are generated straight from the CSS.
  plugins: [react(), tailwindcss()],
  resolve: {
    // `@/...` resolves to `src/...` so imports stay stable as the tree grows.
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // Proxy API calls to the FastAPI backend in dev. The browser talks to the
    // Vite origin only, so there are no CORS surprises during development.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
