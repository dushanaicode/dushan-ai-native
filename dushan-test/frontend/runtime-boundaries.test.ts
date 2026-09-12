// @vitest-environment node

import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { describe, expect, it } from 'vitest';

const frontend = fileURLToPath(
  new URL('../../dushan-admin-frontend/', import.meta.url),
);
const require = createRequire(resolve(frontend, 'package.json'));
const { ESLint } = require('eslint');
const eslint = new ESLint({ cwd: frontend, cache: false });
const ruleId = 'vben-boundaries/runtime-imports';
const runtimeFile = 'packages/effects/request/src/boundary-probe.ts';

async function lint(code: string, file = runtimeFile) {
  const [result] = await eslint.lintText(code, {
    filePath: resolve(frontend, file),
  });
  return result.messages;
}

describe('公共包静态依赖边界', () => {
  it.each([
    [
      "import type { Example } from '#/api/example'; export type Value = Example;",
      'application',
    ],
    ["export type { Example } from '@/store/example';", 'application'],
    [
      "export type { ApiResponse } from '@vben/web-ele/src/api/response';",
      'application',
    ],
    [
      "export type { ApiResponse } from '../../../../apps/web-ele/src/api/response';",
      'application',
    ],
    ["export * from '../../../../internal/node-utils/src/index';", 'tooling'],
    ["export * from '../../../../scripts/vsh/src/index';", 'tooling'],
    ["export { getStagedFiles } from '@vben/node-utils';", 'tooling'],
    ["export { readFile } from 'node:fs/promises';", 'tooling'],
    ["export { readFile } from 'fs/promises';", 'tooling'],
    ["export const load = () => import('#/api/example');", 'application'],
    ['export const load = () => import(`#/api/example`);', 'application'],
    ["export const load = () => require('@vben/vite-config');", 'tooling'],
    [
      "export * from '../../../../node_modules/.pnpm/example@1/node_modules/example';",
      'privateInstall',
    ],
    ["export type Value = import('#/api/example').Example;", 'application'],
    ["export type Stats = import('node:fs').Stats;", 'tooling'],
    [
      "export type Response = import('../../../../apps/web-ele/src/api/response').Response;",
      'application',
    ],
    [
      "export type Private = import('../../../../node_modules/.pnpm/example@1/node_modules/example').Private;",
      'privateInstall',
    ],
  ])('拦截越界静态引用：%s', async (code, messageId) => {
    const messages = await lint(code);
    expect(messages).toEqual(
      expect.arrayContaining([expect.objectContaining({ ruleId, messageId })]),
    );
  });

  it.each([
    "export { computed } from 'vue';",
    "export type { MenuRecordRaw } from '@vben-core/typings';",
    "export { cloneDeep } from '@vben/utils';",
    "export * from './local-module';",
  ])('保留合法引用：%s', async (code) => {
    const messages = await lint(code);
    expect(messages).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ ruleId })]),
    );
  });

  it('公开声明中的类型引用同样遵守应用边界', async () => {
    const messages = await lint(
      "export type { Example } from '#/api/example';",
      'packages/types/global.d.ts',
    );
    expect(messages).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ ruleId, messageId: 'application' }),
      ]),
    );
  });

  it('包的构建入口和测试可以使用 Node 工具，测试仍禁止私有安装路径', async () => {
    const build = await lint(
      "export { defineConfig } from '@vben/vite-config';",
      'packages/@core/base/design/vite.config.ts',
    );
    const test = await lint(
      "export { readFile } from 'node:fs/promises';",
      'packages/@core/composables/src/__tests__/boundary.test.ts',
    );
    for (const messages of [build, test]) {
      expect(messages).not.toEqual(
        expect.arrayContaining([expect.objectContaining({ ruleId })]),
      );
    }
    const privatePath = await lint(
      "export * from '../../../../node_modules/.pnpm/example@1/node_modules/example';",
      'packages/@core/composables/src/__tests__/boundary.test.ts',
    );
    expect(privatePath).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ ruleId, messageId: 'privateInstall' }),
      ]),
    );
  });

  it('原有 core 禁止导入上层包的规则继续生效', async () => {
    const messages = await lint(
      "export { preferences } from '@vben/preferences';",
      'packages/@core/composables/src/boundary-probe.ts',
    );
    expect(messages).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ ruleId: 'no-restricted-imports' }),
      ]),
    );
  });

  it('现有公共包源码满足新增边界规则', async () => {
    const results = await eslint.lintFiles([
      'packages/**/src/**/*.{ts,tsx,js,jsx,vue,mts,cts}',
      'packages/**/*.d.ts',
    ]);
    const violations = results.flatMap(
      (result: {
        filePath: string;
        messages: Array<{
          line: number;
          message: string;
          ruleId: null | string;
        }>;
      }) =>
        result.messages
          .filter((message) => message.ruleId === ruleId)
          .map((message) => ({ file: result.filePath, ...message })),
    );
    expect(violations).toEqual([]);
  });
});
