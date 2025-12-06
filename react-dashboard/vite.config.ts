import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    host: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-ui': ['framer-motion', '@radix-ui/react-dialog', '@radix-ui/react-tabs'],
          'vendor-mqtt': ['mqtt'],
          'vendor-icons': ['lucide-react'],

          // Feature chunks (Phase 4: code splitting for panels)
          'panels-core': [
            './src/components/kiosk/voice-overlay/display-panels/DefaultDisplayPanel',
            './src/components/kiosk/voice-overlay/display-panels/DataDisplayPanel',
          ],
          'panels-control': [
            './src/components/kiosk/voice-overlay/display-panels/LightControlDetailedPanel',
            './src/components/kiosk/voice-overlay/display-panels/MediaControlPanel',
          ],
          'panels-content': [
            './src/components/kiosk/voice-overlay/display-panels/WebViewPanel',
            './src/components/kiosk/voice-overlay/display-panels/SearchResultsPanel',
            './src/components/kiosk/voice-overlay/display-panels/ResearchResultsPanel',
          ],
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
})
