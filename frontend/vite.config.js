import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Local dev: `npm run dev` proxies /api/* straight to the Flask server
// running on :5000, so the app can always call relative "/api/..." paths.
// In production the frontend and backend are two separate Vercel
// deployments, so VITE_API_URL (set in this project's Environment
// Variables) points api.js at the deployed backend's absolute URL instead.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
