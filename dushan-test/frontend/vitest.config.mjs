import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import Vue from '../../dushan-admin-frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs';
import { defineConfig } from '../../dushan-admin-frontend/node_modules/vitest/dist/config.js';

const root = fileURLToPath(new URL('../../', import.meta.url));
const frontend = resolve(root, 'dushan-admin-frontend');
const temporary = resolve(frontend, 'Temp/frontend-foundation');

export default defineConfig({
  root: frontend,
  cacheDir: resolve(temporary, 'vite-cache'),
  plugins: [Vue()],
  server: { fs: { allow: [root] } },
  resolve: {
    conditions: ['development', 'browser'],
    alias: {
      '#': resolve(frontend, 'apps/web-ele/src'),
      '@vben/plugins/vxe-table': resolve(
        frontend,
        'packages/effects/plugins/src/vxe-table/index.ts',
      ),
      '@vben/plugins/tiptap': resolve(
        frontend,
        'packages/effects/plugins/src/tiptap/index.ts',
      ),
      '@vben/locales': resolve(frontend, 'packages/locales/src/index.ts'),
      '@vben/stores': resolve(frontend, 'packages/stores/src/index.ts'),
      '@vben/preferences': resolve(
        frontend,
        'packages/preferences/src/index.ts',
      ),
      pinia: resolve(frontend, 'apps/web-ele/node_modules/pinia'),
      'vue-router': resolve(frontend, 'apps/web-ele/node_modules/vue-router'),
      dayjs: resolve(frontend, 'apps/web-ele/node_modules/dayjs'),
      'element-plus': resolve(
        frontend,
        'apps/web-ele/node_modules/element-plus',
      ),
      vitest: resolve(frontend, 'node_modules/vitest/dist/index.js'),
      vue: resolve(
        frontend,
        'node_modules/vue/dist/vue.runtime.esm-bundler.js',
      ),
      '@vben/request': resolve(
        frontend,
        'packages/effects/request/src/index.ts',
      ),
      '@vben/utils': resolve(frontend, 'packages/utils/src/index.ts'),
    },
  },
  test: {
    environment: 'happy-dom',
    include: [
      resolve(root, 'dushan-test/frontend/**/*.test.ts').replaceAll('\\', '/'),
    ],
    watch: false,
    maxWorkers: 1,
    testTimeout: 60_000,
    reporters: ['default', 'junit'],
    outputFile: { junit: resolve(temporary, 'results.xml') },
  },
});
