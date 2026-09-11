import process from 'node:process';

import { defineConfig, viteCssLayerPlugin } from '@vben/vite-config';

import { loadEnv } from 'vite';

export default defineConfig(async ({ mode }) => {
  return {
    application: {},
    vite: {
      server: {
        proxy: {
          '/api': {
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/api/, ''),
            target: loadEnv(mode, process.cwd()).VITE_API_PROXY_TARGET,
            ws: true,
          },
        },
      },
      plugins: [
        // tdesign 的 css 包进 @layer td，使 Tailwind 工具类可覆盖组件样式
        viteCssLayerPlugin({
          layerName: 'td',
          packageName: 'tdesign-vue-next',
        }),
      ],
    },
  };
});
