import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag) => tag === 'emoji-picker'
        }
      }
    }),
    vueDevTools(),
    /*obfuscator({
      compact: true,
      controlFlowFlattening: false,   // keep false to avoid big perf hit
      deadCodeInjection: false,
      stringArray: true,              // consider disabling if you care about perf
      stringArrayThreshold: 0.3,      // lower threshold -> fewer transformed strings
                                      // additional safe tweaks:
      rotateStringArray: true,
      stringArrayEncoding: false,     // avoid base64/rc4 decoding — adds runtime cost
    })*/
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      '/static': { target: 'http://localhost:8000', changeOrigin: true },
      '/attachments': { target: 'http://localhost:8000', changeOrigin: true },
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    }
  },
  build: {
    sourcemap: false,
    minify: 'esbuild',
  },
})
