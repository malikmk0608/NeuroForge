import { defineConfig } from 'vite'

// Local reference mode. Integrated screens will use authenticated Java routes.
export default defineConfig({
  server: {
    host: '127.0.0.1',
    proxy: { '/portal': 'http://127.0.0.1:8081', '/agent': 'http://127.0.0.1:8002', '/docs': 'http://127.0.0.1:8002', '/openapi.json': 'http://127.0.0.1:8002' },
  },
})
