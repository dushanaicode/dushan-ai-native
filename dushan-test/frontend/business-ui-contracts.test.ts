import { readdirSync, readFileSync } from 'node:fs';
import { basename, resolve } from 'node:path';

import { expect, it } from 'vitest';

import { initComponentAdapter } from '../../dushan-admin-frontend/apps/web-ele/src/adapter/component';
import { globalShareState } from '../../dushan-admin-frontend/packages/effects/common-ui/src/index';

const frontend = process.cwd();
function files(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory()
      ? files(resolve(directory, entry.name))
      : [resolve(directory, entry.name)],
  );
}
function messageKeys(
  value: Record<string, unknown>,
  prefix: string,
  result: Set<string>,
) {
  for (const [name, child] of Object.entries(value)) {
    const key = `${prefix}.${name}`;
    if (typeof child === 'string') result.add(key);
    else messageKeys(child as Record<string, unknown>, key, result);
  }
}

it('业务 Schema 的字符串组件均已注册，避免只有标签没有控件', async () => {
  await initComponentAdapter();
  const registered = new Set([
    ...Object.keys(globalShareState.getComponents()),
    'VbenInputPassword',
  ]);
  const missing = new Set<string>();
  for (const file of files(resolve(frontend, 'apps/web-ele/src/views')).filter(
    (path) => path.endsWith('data.ts'),
  )) {
    for (const match of readFileSync(file, 'utf8').matchAll(
      /component:\s*'([A-Z]\w+)'/g,
    )) {
      if (!registered.has(match[1]!)) missing.add(match[1]!);
    }
  }
  expect([...missing]).toEqual([]);
});

it.each(['zh-CN', 'en-US'])('%s 业务界面引用的静态翻译键均存在', (lang) => {
  const available = new Set<string>();
  for (const directory of [
    'packages/locales/src/langs',
    'apps/web-ele/src/locales/langs',
  ]) {
    for (const file of files(resolve(frontend, directory, lang)).filter(
      (path) => path.endsWith('.json'),
    )) {
      messageKeys(
        JSON.parse(readFileSync(file, 'utf8')),
        basename(file, '.json'),
        available,
      );
    }
  }
  const missing = new Set<string>();
  for (const file of files(resolve(frontend, 'apps/web-ele/src')).filter(
    (path) => /\.(ts|vue)$/.test(path),
  )) {
    for (const match of readFileSync(file, 'utf8').matchAll(
      /\$t\(\s*['"]([^'"]+)['"]/g,
    )) {
      if (!available.has(match[1]!)) missing.add(match[1]!);
    }
  }
  expect([...missing]).toEqual([]);
});
