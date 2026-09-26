import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/Carolina-Data-Challenge-2026/' : '/',
  plugins: [react()],
}))
