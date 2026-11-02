import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  base: './',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // Loopback only: the owner-private view service accepts only these origins.
  server: {
    host: '127.0.0.1',
    port: 3002,
    open: false,
    strictPort: true,
  },
  preview: {
    host: '127.0.0.1',
    port: 3002,
    strictPort: true,
  },
});
