import type { ConfigEnv } from 'vite';

import process from 'node:process';

import { defineConfig, viteCssLayerPlugin } from '@vben/vite-config';

import ElementPlus from 'unplugin-element-plus/vite';
import { loadEnv } from 'vite';

export default defineConfig(async (config) => {
  // Vben 的配置调用方始终传入当前构建环境。
  const { mode } = config as ConfigEnv;
  const target = loadEnv(mode, process.cwd()).VITE_API_PROXY_TARGET;
  return {
    application: {},
    vite: {
      server: {
        proxy: {
          '/admin-api': {
            changeOrigin: true,
            target,
            ws: true,
          },
          // WebSocket 使用独立的同源 /api 通道，转发时剥离该代理前缀。
          '/api': {
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/api/, ''),
            target,
            ws: true,
          },
        },
      },
      plugins: [
        // element-plus 的 css 包进 @layer el，使 Tailwind 工具类可覆盖组件样式
        viteCssLayerPlugin({ layerName: 'el', packageName: 'element-plus' }),
        ElementPlus({ format: 'esm' }),
      ],
    },
  };
});
