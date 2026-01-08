import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Check if we're building for Tauri (production) or browser (development)
const isTauriBuild = process.env.TAURI_ENV_PLATFORM !== undefined;

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },

  // Tauri expects a fixed port, fail if that port is not available
  server: {
    port: 5173,
    strictPort: true,
    // Only use proxy in development (browser mode)
    proxy: isTauriBuild
      ? undefined
      : {
          '/api': {
            target: 'http://localhost:8000',
            changeOrigin: true,
          },
          '/health': {
            target: 'http://localhost:8000',
            changeOrigin: true,
          },
          '/ws': {
            target: 'ws://localhost:8000',
            ws: true,
          },
          '/storage': {
            target: 'http://localhost:8000',
            changeOrigin: true,
          },
        },
  },

  // Tauri-specific configuration
  clearScreen: false,

  // Environment variable prefix
  envPrefix: ['VITE_', 'TAURI_'],

  build: {
    // Tauri uses Chromium on Windows and WebKit on macOS and Linux
    target: process.env.TAURI_ENV_PLATFORM === 'windows' ? 'chrome105' : 'safari13',
    // Reduce chunk size warnings
    chunkSizeWarningLimit: 2000,
    // Minify for production
    minify: !process.env.TAURI_ENV_DEBUG ? 'esbuild' : false,
    // Generate source maps for debug builds
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
    // Optimize output
    rollupOptions: {
      output: {
        manualChunks: {
          // Split vendor chunks for better caching
          'vendor-react': ['react', 'react-dom'],
          'vendor-three': ['three', '@react-three/fiber', '@react-three/drei'],
          'vendor-ui': ['zustand', 'clsx', 'tailwind-merge'],
        },
      },
    },
  },
});
