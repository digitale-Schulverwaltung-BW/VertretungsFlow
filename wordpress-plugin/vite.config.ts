import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
  },
  build: {
    outDir: 'build',
    rollupOptions: {
      output: {
        // Dateien direkt in build/ (nicht build/assets/)
        entryFileNames: 'index.js',
        chunkFileNames: '[name].js',
        assetFileNames: (assetInfo) => {
          // CSS-Dateien als index.css
          if (assetInfo.name && assetInfo.name.endsWith('.css')) {
            return 'index.css';
          }
          // Andere Assets (Fonts, Bilder, etc.)
          return '[name].[ext]';
        },
        // Kein Code-Splitting für WordPress-Plugin
        manualChunks: undefined,
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
})
