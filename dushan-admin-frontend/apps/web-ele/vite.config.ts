import type { ConfigEnv } from 'vite';

import { globSync } from 'node:fs';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

import { defineConfig, viteCssLayerPlugin } from '@vben/vite-config';

import ElementPlus from 'unplugin-element-plus/vite';
import { loadEnv } from 'vite';

export default defineConfig(async (config) => {
  // Vben 的配置调用方始终传入当前构建环境。
  const { mode } = config as ConfigEnv;
  const target = loadEnv(mode, process.cwd()).VITE_API_PROXY_TARGET;
  // 样式入口没有 .d.ts，直接枚举实际文件，避免 Vite 的包导出通配漏选。
  const componentStyles = globSync('*/style/css.mjs', {
    cwd: fileURLToPath(
      new URL(
        'es/components/',
        import.meta.resolve('element-plus/package.json'),
      ),
    ),
  }).map(
    (path) =>
      `element-plus/es/components/${path.replaceAll('\\', '/').slice(0, -4)}`,
  );
  return {
    application: {},
    vite: {
      cacheDir: 'Temp/vite-cache',
      // 插件在页面转换时才注入组件样式；提前预构建，避免首次打开菜单/弹窗触发整页重载。
      optimizeDeps: {
        include: ['jsqr', ...componentStyles],
      },
      resolve: { dedupe: ['vue', 'element-plus'] },
      server: {
        proxy: {
          '/docs': { changeOrigin: true, target },
          '/redoc': { changeOrigin: true, target },
          '/openapi.json': { changeOrigin: true, target },
          '/admin-api': {
            changeOrigin: true,
            target,
            ws: true,
          },
          // WebSocket 后端端点为 /api/ws，转发时保留完整路径。
          '/api': {
            changeOrigin: true,
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
