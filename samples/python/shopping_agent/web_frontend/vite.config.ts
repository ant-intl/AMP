import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const webFrontendPort = Number(process.env.WEB_FRONTEND_PORT) || 8088;
const agentPort = Number(process.env.AGENT_PORT) || 8080;

export default defineConfig({
  plugins: [react()],
  // esbuild 0.28+ refuses to lower destructuring for Vite's default targets
  // (see evanw/esbuild#4436); all default targets support it natively.
  esbuild: {
    supported: {
      destructuring: true,
    },
  },
  // The dev-server dependency pre-bundler runs esbuild separately, so it
  // needs the same destructuring override as the build pipeline above.
  optimizeDeps: {
    esbuildOptions: {
      supported: {
        destructuring: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern',
      },
    },
  },
  server: {
    port: webFrontendPort,
    proxy: {
      '/api': {
        target: `http://localhost:${agentPort}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
