// @vitest-environment node

import { execFile } from 'node:child_process';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { getStagedFiles } from '../../dushan-admin-frontend/internal/node-utils/src/git';

const execute = promisify(execFile);
const frontend = fileURLToPath(
  new URL('../../dushan-admin-frontend/', import.meta.url),
);
const vsh = resolve(frontend, 'scripts/vsh/bin/vsh.mjs');
const temporary = resolve(frontend, 'Temp/frontend-foundation');
const fixtures: string[] = [];
const cycleFiles = {
  'a.ts': "import { b } from './b'; export const a = () => b;",
  'b.ts': "import { a } from './a'; export const b = () => a;",
};

beforeAll(async () => {
  await mkdir(temporary, { recursive: true });
});

afterAll(async () => {
  await Promise.all(
    fixtures.map((directory) =>
      rm(directory, { force: true, recursive: true }),
    ),
  );
});

async function createFixture(files: Record<string, string>) {
  const directory = await mkdtemp(resolve(temporary, 'engineering fixture '));
  fixtures.push(directory);
  for (const [file, content] of Object.entries(files)) {
    const path = resolve(directory, file);
    await mkdir(dirname(path), { recursive: true });
    await writeFile(path, content);
  }
  return directory;
}

async function git(cwd: string, ...args: string[]) {
  return execute('git', ['-c', 'core.autocrlf=false', ...args], { cwd });
}

async function runCli(cwd: string, ...args: string[]) {
  try {
    const result = await execute(process.execPath, [vsh, ...args], {
      cwd,
      env: {
        ...process.env,
        CI: 'true',
        NO_UPDATE_NOTIFIER: '1',
        TEMP: temporary,
        TMP: temporary,
        TMPDIR: temporary,
      },
      timeout: 30_000,
      maxBuffer: 4 * 1024 * 1024,
    });
    return { code: 0, output: result.stdout + result.stderr };
  } catch (error) {
    const failure = error as Error & {
      code?: number | string;
      stderr?: string;
      stdout?: string;
    };
    // 启动失败/超时不能冒充被测命令的正常非零退出。
    if (typeof failure.code !== 'number') throw error;
    return {
      code: failure.code,
      output: (failure.stdout ?? '') + (failure.stderr ?? ''),
    };
  }
}

describe('循环依赖 CLI 的真实退出契约', () => {
  it.each([
    "import type { B } from './b'; export interface A { b?: B }",
    "import { type B } from './b'; export interface A { b?: B }",
  ])('默认排除类型引用，完整图仍报告类型环：%s', async (source) => {
    const directory = await createFixture({
      'a.ts': source,
      'b.ts': "import type { A } from './a'; export interface B { a?: A }",
    });
    const runtime = await runCli(directory, 'check-circular');
    expect(runtime.code).toBe(0);
    expect(runtime.output).toContain('(runtime): 0');
    const allImports = await runCli(
      directory,
      'check-circular',
      '--include-types',
    );
    expect(allImports.code).toBe(1);
    expect(allImports.output).toContain('(all imports): 1');
  });

  it('无循环成功，有循环超过阈值失败，允许的阈值成功', async () => {
    const clean = await createFixture({
      'index.ts': 'export const value = 1;',
    });
    const cleanResult = await runCli(clean, 'check-circular');
    expect(cleanResult.code).toBe(0);

    const cyclic = await createFixture(cycleFiles);
    const rejected = await runCli(cyclic, 'check-circular');
    expect(rejected.code).toBe(1);
    expect(rejected.output).toContain('a.ts');
    const allowed = await runCli(cyclic, 'check-circular', '--threshold', '1');
    expect(allowed.code).toBe(0);
  });

  it.each(['-1', '1.5', 'NaN', 'Infinity'])(
    '拒绝非法阈值 %s',
    async (threshold) => {
      const directory = await createFixture({ 'index.ts': 'export {};' });
      const result = await runCli(
        directory,
        'check-circular',
        `--threshold=${threshold}`,
      );
      expect(result.code).toBe(1);
      expect(result.output).toContain('non-negative integer');
    },
  );

  it.each(['internal/tool', 'scripts/tool', 'packages/effects/request/src'])(
    '默认不会忽略源码目录 %s 中的循环',
    async (prefix) => {
      const directory = await createFixture(
        Object.fromEntries(
          Object.entries(cycleFiles).map(([file, content]) => [
            `${prefix}/${file}`,
            content,
          ]),
        ),
      );
      const result = await runCli(directory, 'check-circular');
      expect(result.code).toBe(1);
    },
  );

  it('暂存模式只判定命中的循环，两个暂存节点仍只计一个循环', async () => {
    const directory = await createFixture({
      ...cycleFiles,
      'other.ts': 'export {};',
    });
    await git(directory, 'init', '--quiet');
    await git(directory, 'add', '--', 'other.ts');
    const unrelated = await runCli(directory, 'check-circular', '--staged');
    expect(unrelated.code).toBe(0);

    await git(directory, 'add', '--', 'a.ts', 'b.ts');
    const related = await runCli(directory, 'check-circular', '--staged');
    expect(related.code).toBe(1);
    const allowed = await runCli(
      directory,
      'check-circular',
      '--staged',
      '--threshold',
      '1',
    );
    expect(allowed.code).toBe(0);
  });

  it('扫描配置引用缺失向外传播', async () => {
    const directory = await createFixture({
      'index.ts': 'export {};',
      'tsconfig.json': JSON.stringify({ extends: './missing-tsconfig.json' }),
    });
    const result = await runCli(directory, 'check-circular');
    expect(result.code).toBe(1);
  });

  it('显式忽略目录只排除指定范围', async () => {
    const directory = await createFixture({
      'generated/a.ts': cycleFiles['a.ts'],
      'generated/b.ts': cycleFiles['b.ts'],
    });
    const result = await runCli(
      directory,
      'check-circular',
      '--ignore-dirs',
      'generated/',
    );
    expect(result.code).toBe(0);
  });

  it.each(['mts', 'cts'])(
    '暂存的 .%s 文件也参与循环判定',
    async (extension) => {
      const directory = await createFixture({
        [`a.${extension}`]: cycleFiles['a.ts'],
        [`b.${extension}`]: cycleFiles['b.ts'],
      });
      await git(directory, 'init', '--quiet');
      await git(directory, 'add', '--', '.');
      const result = await runCli(directory, 'check-circular', '--staged');
      expect(result.code).toBe(1);
    },
  );
});

describe('依赖检查 CLI 的真实退出契约', () => {
  it('配置包通过 require.resolve 使用但未声明的插件仍会失败', async () => {
    const directory = await createFixture({
      'index.js':
        "import { createRequire } from 'node:module'; const require = createRequire(import.meta.url); export const plugin = require.resolve('missing-owned-plugin');",
      'package.json': JSON.stringify({
        name: 'plugin-fixture',
        private: true,
        type: 'module',
      }),
      'knip.json': JSON.stringify({ entry: ['index.js'], oxlint: false }),
    });
    const result = await runCli(directory, 'check-dep');
    expect(result.code).toBe(1);
    expect(result.output).toContain('missing-owned-plugin');
  });

  it('干净项目成功，未使用依赖失败并展示依赖名称', async () => {
    const directory = await createFixture({
      'index.ts': 'export const value = 1;',
      'package.json': JSON.stringify({
        name: 'fixture',
        private: true,
        type: 'module',
      }),
    });
    const clean = await runCli(directory, 'check-dep');
    expect(clean.code).toBe(0);

    await writeFile(
      resolve(directory, 'package.json'),
      JSON.stringify({
        name: 'fixture',
        private: true,
        type: 'module',
        dependencies: { 'unused-frontend-fixture': '1.0.0' },
      }),
    );
    const unused = await runCli(directory, 'check-dep');
    expect(unused.code).toBe(1);
    expect(unused.output).toContain('unused-frontend-fixture');
  });

  it('未声明的导入依赖失败', async () => {
    const directory = await createFixture({
      'index.ts':
        "import value from 'missing-frontend-fixture'; console.log(value);",
      'package.json': JSON.stringify({
        name: 'fixture',
        private: true,
        type: 'module',
      }),
    });
    const result = await runCli(directory, 'check-dep');
    expect(result.code).toBe(1);
    expect(result.output).toContain('missing-frontend-fixture');
  });

  it('工具解析失败不能变成检查通过', async () => {
    const directory = await createFixture({
      'package.json': '{ invalid JSON }',
    });
    const result = await runCli(directory, 'check-dep');
    expect(result.code).toBe(1);
  });
});

describe('父 Git 仓库的前端暂存范围', () => {
  it('子目录返回正确绝对路径，并排除父仓其他项目', async () => {
    const directory = await createFixture({
      'backend/other.ts': 'export {};',
      'frontend/src/带空格 file.ts': 'export {};',
    });
    await git(directory, 'init', '--quiet');
    await git(directory, 'add', '--', '.');
    expect(await getStagedFiles(resolve(directory, 'frontend'))).toEqual([
      resolve(directory, 'frontend/src/带空格 file.ts'),
    ]);
    expect(await getStagedFiles(directory)).toHaveLength(2);
  });

  it('无法访问的工作区明确失败', async () => {
    const directory = await createFixture({ 'index.ts': 'export {};' });
    await expect(getStagedFiles(resolve(directory, 'missing'))).rejects.toThrow(
      /ENOENT/,
    );
  });
});
