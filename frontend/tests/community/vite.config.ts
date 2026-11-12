import path from 'node:path'
import { mergeConfig } from 'vite'
import base from '../../vite.config'

export default mergeConfig(base, {
  resolve: { alias: { '@clerk/react': path.resolve(import.meta.dirname, 'clerkFixture.ts') } },
  plugins: [{
    name: 'community-fixture-entry-only',
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        if (request.url === '/' || request.url?.startsWith('/src/main.tsx')) {
          response.statusCode = 404
          response.end('Use /tests/community/harness.html for fixture verification. Normal app entry is disabled.')
        } else next()
      })
    },
  }],
  server: {
    host: '127.0.0.1', port: 5175, strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:8011', changeOrigin: true } },
  },
})
