import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import crypto from 'node:crypto'

const proxyTarget = process.env.VITE_PROXY_TARGET || 'http://localhost:8000'
const liveGuardSecret = process.env.LIVE_GUARD_SECRET || ''

function signLiveHeaders(proxyReq) {
  if (!liveGuardSecret) return
  const nonce = crypto.randomUUID()
  const timestamp = Math.floor(Date.now() / 1000).toString()
  const signature = crypto
    .createHmac('sha256', liveGuardSecret)
    .update(`${nonce}:${timestamp}`)
    .digest('hex')

  proxyReq.setHeader('X-Live-Nonce', nonce)
  proxyReq.setHeader('X-Live-Timestamp', timestamp)
  proxyReq.setHeader('X-Live-Signature', signature)
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    allowedHosts: true,
    proxy: {
      '/api/v1/trading/execute-live': {
        target: proxyTarget,
        changeOrigin: true,
        rewrite: () => '/api/v1/trading/execute',
        configure(proxy) {
          proxy.on('proxyReq', (proxyReq) => {
            signLiveHeaders(proxyReq)
          })
        },
      },
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
    },
  },
})